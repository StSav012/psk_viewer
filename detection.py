# -*- coding: utf-8 -*-

from typing import Final

import numpy as np

LINE_WIDTH: Final[float] = 2.6e6


def remove_spikes(sequence: np.ndarray, iterations: int = 1) -> np.ndarray:
    from scipy import ndimage  # type: ignore

    sequence = ndimage.binary_dilation(sequence, iterations=iterations)
    sequence = ndimage.binary_erosion(sequence, iterations=iterations + 1)
    sequence = ndimage.binary_dilation(sequence, iterations=1)
    return sequence


def correlation(model_y, another_x: np.ndarray, another_y: np.ndarray) -> np.ndarray:
    from scipy.signal import butter, lfilter  # type: ignore

    def butter_bandpass_filter(data: np.ndarray, low_cut: float, high_cut: float, order: int = 5):
        def butter_bandpass():
            nyq: float = 0.5 * fs
            low: float = low_cut / nyq
            high: float = high_cut / nyq
            if low > 0. and high < fs:
                return butter(order, [low, high], btype='bandpass')
            if low > 0. and high >= fs:
                return butter(order, low, btype='highpass')
            if low <= 0. and high < fs:
                return butter(order, high, btype='lowpass')
            raise ValueError

        return lfilter(*butter_bandpass(), data)

    if another_y.size:
        fs: float = 1.0 / (another_x[1] - another_x[0])
        another_y_filtered: np.ndarray = butter_bandpass_filter(another_y,
                                                                low_cut=0.005 * fs, high_cut=np.inf,
                                                                order=5)
        _corr: np.ndarray = np.correlate(another_y_filtered, model_y, 'same')
        _corr -= np.mean(_corr)
        _corr /= np.std(_corr)
        return _corr
    return np.empty(0)


def peaks_positions(data_x: np.ndarray, data_y: np.ndarray, threshold: float = 0.0046228) -> np.ndarray:
    import pandas as pd  # type: ignore
    if data_x.size < 2 or data_y.size < 2:
        # nothing to do
        return np.empty(0)

    std: np.ndarray = pd.Series(data_y).rolling(int(round(LINE_WIDTH / (data_x[1] - data_x[0]))),
                                                center=True).std().to_numpy()
    match: np.ndarray = np.array((std >= np.nanquantile(std, 1.0 - threshold)))
    match = remove_spikes(match, iterations=8)
    match[0] = match[-1] = False
    islands: np.ndarray = np.argwhere(np.diff(match)).reshape(-1, 2)
    peaks: np.ndarray = np.array([i[0] + np.argmax(data_y[i[0]:i[1]])
                                  for i in islands
                                  if (np.argmax(data_y[i[0]:i[1]]) not in (0, i[1] - i[0]))])
    return peaks
