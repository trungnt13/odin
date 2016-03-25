# -*- coding: utf-8 -*-
# ===========================================================================
# The waveform and spectrogram plot adapted from:
# [librosa](https://github.com/bmcfee/librosa)
# Copyright (c) 2016, librosa development team.
# Modified work Copyright 2016-2017 TrungNT
# ===========================================================================

from __future__ import print_function, absolute_import, division

import copy
import numpy as np
from six.moves import zip, range
from .. import logger
from ..features import preprocess as pp
import warnings


# ===========================================================================
# Helper for spectrogram
# ===========================================================================
def time_ticks(locs, *args, **kwargs):  # pylint: disable=star-args
    '''Plot time-formatted axis ticks.
    Parameters
    ----------
    locations : list or np.ndarray
        Time-stamps for tick marks
    n_ticks : int > 0 or None
        Show this number of ticks (evenly spaced).
        If none, all ticks are displayed.
        Default: 5
    axis : 'x' or 'y'
        Which axis should the ticks be plotted on?
        Default: 'x'
    time_fmt : None or {'ms', 's', 'm', 'h'}
        - 'ms': milliseconds   (eg, 241ms)
        - 's': seconds         (eg, 1.43s)
        - 'm': minutes         (eg, 1:02)
        - 'h': hours           (eg, 1:02:03)
        If none, formatted is automatically selected by the
        range of the times data.
        Default: None
    fmt : str
        .. warning:: This parameter name was in librosa 0.4.2
            Use the `time_fmt` parameter instead.
            The `fmt` parameter will be removed in librosa 0.5.0.
    kwargs : additional keyword arguments.
        See `matplotlib.pyplot.xticks` or `yticks` for details.
    Returns
    -------
    locs
    labels
        Locations and labels of tick marks
    See Also
    --------
    matplotlib.pyplot.xticks
    matplotlib.pyplot.yticks
    Examples
    --------
    >>> # Tick at pre-computed beat times
    >>> librosa.display.specshow(S)
    >>> librosa.display.time_ticks(beat_times)
    >>> # Set the locations of the time stamps
    >>> librosa.display.time_ticks(locations, timestamps)
    >>> # Format in seconds
    >>> librosa.display.time_ticks(beat_times, time_fmt='s')
    >>> # Tick along the y axis
    >>> librosa.display.time_ticks(beat_times, axis='y')
    '''
    from matplotlib import pyplot as plt

    n_ticks = kwargs.pop('n_ticks', 5)
    axis = kwargs.pop('axis', 'x')
    time_fmt = kwargs.pop('time_fmt', None)

    if axis == 'x':
        ticker = plt.xticks
    elif axis == 'y':
        ticker = plt.yticks
    else:
        raise ValueError("axis must be either 'x' or 'y'.")

    if len(args) > 0:
        times = args[0]
    else:
        times = locs
        locs = np.arange(len(times))

    if n_ticks is not None:
        # Slice the locations and labels evenly between 0 and the last point
        positions = np.linspace(0, len(locs) - 1, n_ticks,
                                endpoint=True).astype(int)
        locs = locs[positions]
        times = times[positions]

    # Format the labels by time
    formats = {'ms': lambda t: '{:d}ms'.format(int(1e3 * t)),
               's': '{:0.2f}s'.format,
               'm': lambda t: '{:d}:{:02d}'.format(int(t / 6e1),
                                                   int(np.mod(t, 6e1))),
               'h': lambda t: '{:d}:{:02d}:{:02d}'.format(int(t / 3.6e3),
                                                          int(np.mod(t / 6e1,
                                                                     6e1)),
                                                          int(np.mod(t, 6e1)))}

    if time_fmt is None:
        if max(times) > 3.6e3:
            time_fmt = 'h'
        elif max(times) > 6e1:
            time_fmt = 'm'
        elif max(times) > 1.0:
            time_fmt = 's'
        else:
            time_fmt = 'ms'

    elif time_fmt not in formats:
        raise ValueError('Invalid format: {:s}'.format(time_fmt))

    times = [formats[time_fmt](t) for t in times]

    return ticker(locs, times, **kwargs)


def _cmap(data):
    '''Get a default colormap from the given data.

    If the data is boolean, use a black and white colormap.

    If the data has both positive and negative values,
    use a diverging colormap ('coolwarm').

    Otherwise, use a sequential map: either cubehelix or 'OrRd'.

    Parameters
    ----------
    data : np.ndarray
        Input data


    Returns
    -------
    cmap : matplotlib.colors.Colormap
        - If `data` has dtype=boolean, `cmap` is 'gray_r'
        - If `data` has only positive or only negative values,
          `cmap` is 'OrRd' (`use_sns==False`) or cubehelix
        - If `data` has both positive and negatives, `cmap` is 'coolwarm'

    See Also
    --------
    matplotlib.pyplot.colormaps
    seaborn.cubehelix_palette
    '''
    import matplotlib as mpl
    from matplotlib import pyplot as plt

    _HAS_SEABORN = False
    try:
        _matplotlibrc = copy.deepcopy(mpl.rcParams)
        import seaborn as sns
        _HAS_SEABORN = True
        mpl.rcParams.update(**_matplotlibrc)
    except ImportError:
        pass

    data = np.atleast_1d(data)

    if data.dtype == 'bool':
        return plt.get_cmap('gray_r')

    data = data[np.isfinite(data)]

    robust = True
    if robust:
        min_p, max_p = 2, 98
    else:
        min_p, max_p = 0, 100

    max_val = np.percentile(data, max_p)
    min_val = np.percentile(data, min_p)

    if min_val >= 0 or max_val <= 0:
        if _HAS_SEABORN:
            return sns.cubehelix_palette(light=1.0, as_cmap=True)
        else:
            return plt.get_cmap('OrRd')

    return plt.get_cmap('coolwarm')


# ===========================================================================
# Helpers
# From DeepLearningTutorials: http://deeplearning.net
# ===========================================================================
def resize_images(x, shape):
    from scipy.misc import imresize

    reszie_func = lambda x, shape: imresize(x, shape, interp='bilinear')
    if x.ndim == 4:
        def reszie_func(x, shape):
            # x: 3D
            # The color channel is the first dimension
            tmp = []
            for i in x:
                tmp.append(imresize(i, shape).reshape((-1,) + shape))
            return np.swapaxes(np.vstack(tmp).T, 0, 1)

    imgs = []
    for i in x:
        imgs.append(reszie_func(i, shape))
    return imgs


def tile_raster_images(X, tile_shape=None, tile_spacing=(2, 2), spacing_value=0.):
    ''' This function create tile of images

    Parameters
    ----------
    X : 3D-gray or 4D-color images
        for color images, the color channel must be the second dimension
    tile_shape : tuple
        resized shape of images
    tile_spacing : tuple
        space betwen rows and columns of images
    spacing_value : int, float
        value used for spacing

    '''
    if X.ndim == 3:
        img_shape = X.shape[1:]
    elif X.ndim == 4:
        img_shape = X.shape[2:]
    else:
        raise ValueError('Unsupport %d dimension images' % X.ndim)
    if tile_shape is None:
        tile_shape = img_shape
    if tile_spacing is None:
        tile_spacing = (2, 2)

    if img_shape != tile_shape:
        X = resize_images(X, tile_shape)
    else:
        X = [np.swapaxes(x.T, 0, 1) for x in X]

    n = len(X)
    n = int(np.ceil(np.sqrt(n)))

    # create spacing
    rows_spacing = np.zeros_like(X[0])[:tile_spacing[0], :] + spacing_value
    nothing = np.vstack((np.zeros_like(X[0]), rows_spacing))
    cols_spacing = np.zeros_like(nothing)[:, :tile_spacing[1]] + spacing_value

    # ====== Append columns ====== #
    rows = []
    for i in range(n): # each rows
        r = []
        for j in range(n): # all columns
            idx = i * n + j
            if idx < len(X):
                r.append(np.vstack((X[i * n + j], rows_spacing)))
            else:
                r.append(nothing)
            if j != n - 1:   # cols spacing
                r.append(cols_spacing)
        rows.append(np.hstack(r))
    # ====== Append rows ====== #
    img = np.vstack(rows)[:-tile_spacing[0]]
    return img


# ===========================================================================
# Plotting methods
# ===========================================================================
def plot_waveplot(y, sr=22050, ax=None,
                  max_points=5e4, x_axis='time', offset=0.0,
                  max_sr=1000, time_fmt=None, **kwargs):
    '''Plot the amplitude envelope of a waveform.

    If `y` is monophonic, a filled curve is drawn between `[-abs(y), abs(y)]`.

    If `y` is stereo, the curve is drawn between `[-abs(y[1]), abs(y[0])]`,
    so that the left and right channels are drawn above and below the axis,
    respectively.

    Long signals (`duration >= max_points`) are down-sampled to at
    most `max_sr` before plotting.

    Parameters
    ----------
    y : np.ndarray [shape=(n,) or (2,n)]
        audio time series (mono or stereo)

    sr : number > 0 [scalar]
        sampling rate of `y`

    max_points : postive number or None
        Maximum number of time-points to plot: if `max_points` exceeds
        the duration of `y`, then `y` is downsampled.

        If `None`, no downsampling is performed.

    x_axis : str {'time', 'off', 'none'} or None
        If 'time', the x-axis is given time tick-marks.

        See also: `time_ticks`

    offset : float
        Horizontal offset (in time) to start the waveform plot

    max_sr : number > 0 [scalar]
        Maximum sampling rate for the visualization

    time_fmt : None or str
        Formatting for time axis.  None (automatic) by default.

        See `time_ticks`.

    kwargs
        Additional keyword arguments to `matplotlib.pyplot.fill_between`

    Returns
    -------
    pc : matplotlib.collections.PolyCollection
        The PolyCollection created by `fill_between`.

    See also
    --------
    time_ticks
    librosa.core.resample
    matplotlib.pyplot.fill_between


    Examples
    --------
    Plot a monophonic waveform

    >>> import matplotlib.pyplot as plt
    >>> y, sr = librosa.load(librosa.util.example_audio_file(), duration=10)
    >>> plt.figure()
    >>> plt.subplot(3, 1, 1)
    >>> librosa.display.waveplot(y, sr=sr)
    >>> plt.title('Monophonic')

    Or a stereo waveform

    >>> y, sr = librosa.load(librosa.util.example_audio_file(),
    ...                      mono=False, duration=10)
    >>> plt.subplot(3, 1, 2)
    >>> librosa.display.waveplot(y, sr=sr)
    >>> plt.title('Stereo')

    Or harmonic and percussive components with transparency

    >>> y, sr = librosa.load(librosa.util.example_audio_file(), duration=10)
    >>> y_harm, y_perc = librosa.effects.hpss(y)
    >>> plt.subplot(3, 1, 3)
    >>> librosa.display.waveplot(y_harm, sr=sr, alpha=0.25)
    >>> librosa.display.waveplot(y_perc, sr=sr, color='r', alpha=0.5)
    >>> plt.title('Harmonic + Percussive')
    >>> plt.tight_layout()
    '''
    from matplotlib import pyplot as plt

    pp.valid_audio(y, mono=False)

    if not (isinstance(max_sr, int) and max_sr > 0):
        raise ValueError('max_sr must be a non-negative integer')

    target_sr = sr

    if max_points is not None:
        if max_points <= 0:
            raise ValueError('max_points must be strictly positive')

        if max_points < y.shape[-1]:
            target_sr = min(max_sr, (sr * y.shape[-1]) // max_points)

        hop_length = sr // target_sr

        if y.ndim == 1:
            # Compute the max-envelope of x at a stride/frame length of h
            y = pp.frame(y, hop_length=hop_length, frame_length=hop_length).max(axis=0)
        else:
            y = np.vstack([
                pp.frame(_, hop_length=hop_length, frame_length=hop_length).max(axis=0)
                for _ in y])

    if y.ndim > 1:
        y_top = y[0]
        y_bottom = -y[1]
    else:
        y_top = y
        y_bottom = -y

    if ax is None:
        axes = plt.gca()
    else:
        axes = ax

    if hasattr(axes._get_lines, 'prop_cycler'):
        # matplotlib >= 1.5
        kwargs.setdefault('color', next(axes._get_lines.prop_cycler)['color'])
    else:
        # matplotlib 1.4
        kwargs.setdefault('color', next(axes._get_lines.color_cycle))

    sample_off = pp.time_to_samples(offset, sr=target_sr)

    locs = np.arange(sample_off, sample_off + len(y_top))
    out = axes.plot(y, **kwargs)
    # fill_between(locs, y_bottom, y_top, **kwargs)

    plt.xlim([locs[0], locs[-1]])

    if x_axis == 'time':
        time_ticks(locs,
            pp.samples_to_time(locs, sr=target_sr), time_fmt=time_fmt)
    elif x_axis is None or x_axis in ['off', 'none']:
        plt.xticks([])
    else:
        raise ValueError('Unknown x_axis value: {}'.format(x_axis))

    return out


def plot_spectrogram(x, vad=None, ax=None, colorbar=False):
    '''
    Parameters
    ----------
    x : np.ndarray
        2D array
    vad : np.ndarray, list
        1D array, a red line will be draw at vad=1.
    ax : matplotlib.Axis
        create by fig.add_subplot, or plt.subplots
    colorbar : bool, 'all'
        whether adding colorbar to plot, if colorbar='all', call this
        methods after you add all subplots will create big colorbar
        for all your plots
    path : str
        if path is specified, save png image to given path

    Notes
    -----
    Make sure nrow and ncol in add_subplot is int or this error will show up
     - ValueError: The truth value of an array with more than one element is
        ambiguous. Use a.any() or a.all()

    Example
    -------
    >>> x = np.random.rand(2000, 1000)
    >>> fig = plt.figure()
    >>> ax = fig.add_subplot(2, 2, 1)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 2)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 3)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 4)
    >>> dnntoolkit.visual.plot_weights(x, ax, path='/Users/trungnt13/tmp/shit.png')
    >>> plt.show()
    '''
    from matplotlib import pyplot as plt

    # colormap = _cmap(x)
    colormap = 'spectral'

    if x.ndim > 2:
        raise ValueError('No support for > 2D')
    elif x.ndim == 1:
        x = x[:, None]

    if vad is not None:
        vad = np.asarray(vad).ravel()
        if len(vad) != x.shape[1]:
            raise ValueError('Length of VAD must equal to signal length, but '
                             'length[vad]={} != length[signal]={}'.format(
                                 len(vad), x.shape[1]))
        # normalize vad
        vad = np.cast[np.bool](vad)

    ax = ax if ax is not None else plt.gca()
    ax.set_aspect('equal', 'box')
    # ax.tick_params(axis='both', which='major', labelsize=6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    ax.set_title(str(x.shape), fontsize=6)
    img = ax.pcolorfast(x, cmap=colormap, alpha=0.9)
    # ====== draw vad vertical line ====== #
    if vad is not None:
        for i, j in enumerate(vad):
            if j:
                ax.axvline(
                    x=i, ymin=0, ymax=1, color='r', linewidth=1, alpha=0.4)
    plt.grid(True)

    if colorbar == 'all':
        fig = ax.get_figure()
        axes = fig.get_axes()
        fig.colorbar(img, ax=axes)
    elif colorbar:
        plt.colorbar(img, ax=ax)

    return ax


def plot_images(X, tile_shape=None, tile_spacing=None, fig=None, title=None):
    '''
    x : 2D-gray or 3D-color images, or list of (2D, 3D images)
        for color image the color channel is second dimension
    '''
    from matplotlib import pyplot as plt
    if not isinstance(X, (tuple, list)):
        X = [X]
    if not isinstance(title, (tuple, list)):
        title = [title]

    n = int(np.ceil(np.sqrt(len(X))))
    for i, (x, t) in enumerate(zip(X, title)):
        if x.ndim == 3 or x.ndim == 2:
            cmap = plt.cm.Greys_r
        elif x.ndim == 4:
            cmap = None
        else:
            raise ValueError('NO support for %d dimensions image!' % x.ndim)

        x = tile_raster_images(x, tile_shape, tile_spacing)
        if fig is None:
            fig = plt.figure()
        subplot = fig.add_subplot(n, n, i + 1)
        subplot.imshow(x, cmap=cmap)
        if t is not None:
            subplot.set_title(str(t), fontsize=12)
        subplot.axis('off')

    fig.tight_layout()
    return fig


def plot_images_old(x, fig=None, titles=None, show=False):
    '''
    x : 2D-gray or 3D-color images
        for color image the color channel is second dimension
    '''
    from matplotlib import pyplot as plt
    if x.ndim == 3 or x.ndim == 2:
        cmap = plt.cm.Greys_r
    elif x.ndim == 4:
        cmap = None
        shape = x.shape[2:] + (x.shape[1],)
        x = np.vstack([i.T.reshape((-1,) + shape) for i in x])
    else:
        raise ValueError('NO support for %d dimensions image!' % x.ndim)

    if x.ndim == 2:
        ncols = 1
        nrows = 1
    else:
        ncols = int(np.ceil(np.sqrt(x.shape[0])))
        nrows = int(ncols)

    if fig is None:
        fig = plt.figure()
    if titles is not None:
        if not isinstance(titles, (tuple, list)):
            titles = [titles]
        if len(titles) != x.shape[0]:
            raise ValueError('Titles must have the same length with \
                the number of images!')

    for i in range(ncols):
        for j in range(nrows):
            idx = i * ncols + j
            if idx < x.shape[0]:
                subplot = fig.add_subplot(nrows, ncols, idx + 1)
                subplot.imshow(x[idx], cmap=cmap)
                if titles is not None:
                    subplot.set_title(titles[idx])
                subplot.axis('off')

    if show:
        # plt.tight_layout()
        plt.show(block=True)
        raw_input('<Enter> to close the figure ...')
    else:
        return fig


def plot_confusion_matrix(cm, labels, axis=None, fontsize=13):
    from matplotlib import pyplot as plt

    title = 'Confusion matrix'
    cmap = plt.cm.Blues

    # column normalize
    if np.max(cm) > 1:
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    else:
        cm_normalized = cm
    if axis is None:
        axis = plt.gca()

    im = axis.imshow(cm_normalized, interpolation='nearest', cmap=cmap)
    axis.set_title(title)
    axis.get_figure().colorbar(im)

    tick_marks = np.arange(len(labels))
    axis.set_xticks(tick_marks)
    axis.set_yticks(tick_marks)
    axis.set_xticklabels(labels, rotation=90, fontsize=13)
    axis.set_yticklabels(labels, fontsize=13)
    axis.set_ylabel('True label')
    axis.set_xlabel('Predicted label')
    # axis.tight_layout()
    return axis


def plot_weights(x, ax=None, colormap = "Greys", colorbar=False, keep_aspect=True):
    '''
    Parameters
    ----------
    x : np.ndarray
        2D array
    ax : matplotlib.Axis
        create by fig.add_subplot, or plt.subplots
    colormap : str
        colormap alias from plt.cm.Greys = 'Greys' ('spectral')
        plt.cm.gist_heat
    colorbar : bool, 'all'
        whether adding colorbar to plot, if colorbar='all', call this
        methods after you add all subplots will create big colorbar
        for all your plots
    path : str
        if path is specified, save png image to given path

    Notes
    -----
    Make sure nrow and ncol in add_subplot is int or this error will show up
     - ValueError: The truth value of an array with more than one element is
        ambiguous. Use a.any() or a.all()

    Example
    -------
    >>> x = np.random.rand(2000, 1000)
    >>> fig = plt.figure()
    >>> ax = fig.add_subplot(2, 2, 1)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 2)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 3)
    >>> dnntoolkit.visual.plot_weights(x, ax)
    >>> ax = fig.add_subplot(2, 2, 4)
    >>> dnntoolkit.visual.plot_weights(x, ax, path='/Users/trungnt13/tmp/shit.png')
    >>> plt.show()
    '''
    from matplotlib import pyplot as plt

    if colormap is None:
        colormap = plt.cm.Greys

    if x.ndim > 2:
        raise ValueError('No support for > 2D')
    elif x.ndim == 1:
        x = x[:, None]

    ax = ax if ax is not None else plt.gca()
    if keep_aspect:
        ax.set_aspect('equal', 'box')
    # ax.tick_params(axis='both', which='major', labelsize=6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    ax.set_title(str(x.shape), fontsize=6)
    img = ax.pcolorfast(x, cmap=colormap, alpha=0.8)
    plt.grid(True)

    if colorbar == 'all':
        fig = ax.get_figure()
        axes = fig.get_axes()
        fig.colorbar(img, ax=axes)
    elif colorbar:
        plt.colorbar(img, ax=ax)

    return ax


def plot_weights3D(x, colormap = "Greys"):
    '''
    Example
    -------
    >>> # 3D shape
    >>> x = np.random.rand(32, 28, 28)
    >>> dnntoolkit.visual.plot_conv_weights(x)
    '''
    from matplotlib import pyplot as plt

    if colormap is None:
        colormap = plt.cm.Greys

    shape = x.shape
    if len(shape) == 3:
        ncols = int(np.ceil(np.sqrt(shape[0])))
        nrows = int(ncols)
    else:
        raise ValueError('This function only support 3D weights matrices')

    fig = plt.figure()
    count = 0
    for i in range(nrows):
        for j in range(ncols):
            count += 1
            # skip
            if count > shape[0]:
                continue

            ax = fig.add_subplot(nrows, ncols, count)
            # ax.set_aspect('equal', 'box')
            ax.set_xticks([])
            ax.set_yticks([])
            if i == 0 and j == 0:
                ax.set_xlabel('Width:%d' % x.shape[-1], fontsize=6)
                ax.xaxis.set_label_position('top')
                ax.set_ylabel('Height:%d' % x.shape[-2], fontsize=6)
                ax.yaxis.set_label_position('left')
            else:
                ax.axis('off')
            # image data: no idea why pcolorfast flip image vertically
            img = ax.pcolorfast(x[count - 1][::-1, :], cmap=colormap, alpha=0.9)
            # plt.grid(True)

    plt.tight_layout()
    # colorbar
    axes = fig.get_axes()
    fig.colorbar(img, ax=axes)

    return fig


def plot_weights4D(x, colormap = "Greys"):
    '''
    Example
    -------
    >>> # 3D shape
    >>> x = np.random.rand(32, 28, 28)
    >>> dnntoolkit.visual.plot_conv_weights(x)
    '''
    from matplotlib import pyplot as plt

    if colormap is None:
        colormap = plt.cm.Greys

    shape = x.shape
    if len(shape) != 4:
        raise ValueError('This function only support 4D weights matrices')

    fig = plt.figure()
    imgs = []
    for i in range(shape[0]):
        imgs.append(tile_raster_images(x[i], tile_spacing=(3, 3)))

    ncols = int(np.ceil(np.sqrt(shape[0])))
    nrows = int(ncols)

    count = 0
    for i in range(nrows):
        for j in range(ncols):
            count += 1
            # skip
            if count > shape[0]:
                continue

            ax = fig.add_subplot(nrows, ncols, count)
            ax.set_aspect('equal', 'box')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis('off')
            # image data: no idea why pcolorfast flip image vertically
            img = ax.pcolorfast(imgs[count - 1][::-1, :], cmap=colormap, alpha=0.9)

    plt.tight_layout()
    # colorbar
    axes = fig.get_axes()
    fig.colorbar(img, ax=axes)

    return fig


def plot_hinton(matrix, max_weight=None, ax=None):
    '''
    Hinton diagrams are useful for visualizing the values of a 2D array (e.g.
    a weight matrix):
        Positive: white
        Negative: black
    squares, and the size of each square represents the magnitude of each value.
    * Note: performance significant decrease as array size > 50*50
    Example:
        W = np.random.rand(10,10)
        hinton_plot(W)
    '''
    from matplotlib import pyplot as plt

    """Draw Hinton diagram for visualizing a weight matrix."""
    ax = ax if ax is not None else plt.gca()

    if not max_weight:
        max_weight = 2**np.ceil(np.log(np.abs(matrix).max()) / np.log(2))

    ax.patch.set_facecolor('gray')
    ax.set_aspect('equal', 'box')
    ax.xaxis.set_major_locator(plt.NullLocator())
    ax.yaxis.set_major_locator(plt.NullLocator())

    for (x, y), w in np.ndenumerate(matrix):
        color = 'white' if w > 0 else 'black'
        size = np.sqrt(np.abs(w))
        rect = plt.Rectangle([x - size / 2, y - size / 2], size, size,
                             facecolor=color, edgecolor=color)
        ax.add_patch(rect)

    ax.autoscale_view()
    ax.invert_yaxis()
    return ax


# ===========================================================================
# Helper methods
# ===========================================================================
def plot_show():
    from matplotlib import pyplot as plt
    plt.show(block=False)
    raw_input('<enter> to close all plots')
    plt.close('all')


def plot_close():
    from matplotlib import pyplot as plt
    plt.close('all')


def plot_save(path, figs=None, dpi=300):
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        pp = PdfPages(path)
        if figs is None:
            figs = [plt.figure(n) for n in plt.get_fignums()]
        for fig in figs:
            fig.savefig(pp, format='pdf')
        pp.close()
        logger.info('Saved pdf figures to:%s' % str(path))
    except Exception, e:
        logger.error('Cannot save figures to pdf, error:%s' % str(e))
