#cython: cdivision=True
#cython: boundscheck=False
#cython: nonecheck=False
#cython: wraparound=False

"""Cython code wrapped in extrema.py."""

cimport numpy as cnp


# Must be defined to use RestorableQueue
ctypedef Py_ssize_t QueueItem

include "_restorable_queue.pxi"


ctypedef fused dtype_t:
    cnp.uint64_t
    cnp.int64_t
    cnp.float64_t


# Definition of flag values used for `flags` in _local_maxima & _fill_plateau
cdef:
    # First or last index in a dimension
    unsigned char BORDER_INDEX = 3
    # Potentially part of a maximum
    unsigned char MAYBE_MAXIMUM = 2
    # Index was queued (flood-fill) and might still be part of maximum
    unsigned char QUEUED_MAYBE_MAXIMUM = 1
    # None of the above is true
    unsigned char NOT_MAXIMUM = 0


def _local_maxima(dtype_t[::1] image not None,
                  unsigned char[::1] flags,
                  Py_ssize_t[::1] neighbor_offsets not None):
    """Detect local maxima in n-dimensional array.

    Parameters
    ----------
    image : ndarray, one-dimensional
        The raveled view of a n-dimensional array.
    flags : ndarray
        An array of flags that is used to store the state of each pixel during
        evaluation.
    neighbor_offsets : ndarray
        A one-dimensional array that contains the offsets to find the
        connected neighbors for any index in `image`.

    Returns
    -------
    is_maximum : ndarray
        A "boolean" array that is 1 where local maxima exist.
    """
    cdef:
        RestorableQueue queue
        Py_ssize_t i, i_max, i_ahead
        unsigned char prefilter

    # Prefilter candidates only if neighbors in last dimension are part of
    # the structuring element
    prefilter = -1 in neighbor_offsets and 1 in neighbor_offsets
    with nogil:
        i = 1
        i_max = image.shape[0]

        if prefilter:
            while i < i_max:
                if image[i - 1] < image[i] and flags[i] != BORDER_INDEX:
                    # Potential maximum (in last dimension) is found, find
                    # other edge of current plateau or "edge of dimension"
                    i_ahead = i + 1
                    while (
                        image[i] == image[i_ahead] and
                        flags[i_ahead] != BORDER_INDEX
                    ):
                        i_ahead += 1
                    if image[i] > image[i_ahead]:
                        # Found local maximum (in one dimension), mark all
                        # parts of the plateau as potential maximum
                        flags[i:i_ahead] = MAYBE_MAXIMUM
                    i = i_ahead
                else:
                    i += 1

        else:  # Skip prefiltering and flag entire array as potential maximum
            while i < i_max:
                if flags[i] != BORDER_INDEX:
                    flags[i] = MAYBE_MAXIMUM
                i += 1

        # Initialize a buffer used to queue positions while evaluating each
        # potential maximum (flagged with 2)
        queue_init(&queue, 64)
        try:
            for i in range(image.shape[0]):
                if flags[i] == MAYBE_MAXIMUM:
                    # Index is potentially part of a maximum:
                    # Find all samples part of the plateau and fill with 0
                    # or 1 depending on whether it's a true maximum
                    _fill_plateau(image, flags, neighbor_offsets, &queue, i)
        finally:
            queue_exit(&queue)


cdef inline void _fill_plateau(
        dtype_t[::1] image, unsigned char[::1] flags,
        Py_ssize_t[::1] neighbor_offsets, RestorableQueue* queue_ptr,
        Py_ssize_t start_index) nogil:
    """Fill with 1 if plateau is local maximum else with 0.
    
    Parameters
    ----------
    image :
        The raveled view of a n-dimensional array.
    flags :
        An array of flags that is used to store the state of each pixel during
        evaluation.
    neighbor_offsets :
        A one-dimensional array that contains the offsets to find the
        connected neighbors for any index in `image`.
    queue_ptr :
        Pointer to initialized queue.
    start_index :
        Start position for the flood-fill.
    """
    cdef:
        dtype_t h
        unsigned char true_maximum
        QueueItem current_index, neighbor

    h = image[start_index]
    true_maximum = 1 # Boolean flag

    flags[start_index] = QUEUED_MAYBE_MAXIMUM

    # And queue start position after clearing the buffer
    queue_clear(queue_ptr)
    queue_push(queue_ptr, &start_index)

    # Break loop if all queued positions were evaluated
    while queue_pop(queue_ptr, &current_index):
        # Look at all neighbouring samples
        for i in range(neighbor_offsets.shape[0]):
            neighbor = current_index + neighbor_offsets[i]

            if image[neighbor] == h:
                # Value is part of plateau
                if flags[neighbor] == BORDER_INDEX:
                    # Plateau touches border and can't be maximum
                    true_maximum = NOT_MAXIMUM
                elif flags[neighbor] != QUEUED_MAYBE_MAXIMUM:
                    # Index wasn't queued already, do so now
                    queue_push(queue_ptr, &neighbor)
                    flags[neighbor] = QUEUED_MAYBE_MAXIMUM

            elif image[neighbor] > h:
                # Current plateau can't be maximum because it borders a
                # larger one
                true_maximum = NOT_MAXIMUM

    if not true_maximum:
        queue_restore(queue_ptr)
        # Initial guess was wrong -> replace 1 with 0 for plateau
        while queue_pop(queue_ptr, &neighbor):
            flags[neighbor] = NOT_MAXIMUM
