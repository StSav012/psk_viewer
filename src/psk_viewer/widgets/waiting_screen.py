from collections.abc import Callable, Mapping, Sequence
from threading import Thread
from typing import Any, Generic, TypeVar

from qtpy.QtCore import QCoreApplication, QMargins, QSize, Qt
from qtpy.QtGui import QKeySequence, QTextDocument
from qtpy.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

__all__ = ["WaitingScreen"]


def _spinner(parent: QWidget | None = None) -> QWidget | None:
    from contextlib import suppress

    with suppress(ImportError, Exception):
        import qtawesome as qta

        spinner: qta.IconWidget = qta.IconWidget(parent=parent)
        size: int = spinner.fontMetrics().height() * 2
        spinner.setIconSize(QSize(size, size))
        # might raise an `Exception` if the icon is not in the font
        spinner.setIcon(
            qta.icon("mdi6.loading", animation=qta.Spin(spinner, interval=16, step=4))
        )
        spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return spinner

    return None


_T = TypeVar("_T")


class _Thread(Thread, Generic[_T]):
    def __init__(
        self,
        target: Callable[..., _T] | None,
        args: Sequence[object],
        kwargs: Mapping[str, object],
    ) -> None:
        super().__init__(daemon=True)

        self._target: Callable[..., _T] | None = target
        self._args: Sequence[Any] = args
        self._kwargs: Mapping[str, Any] = kwargs or dict()

        self._result: _T | None = None

    def result(self) -> _T | None:
        return self._result

    def run(self) -> None:
        if self._target is not None:
            try:
                self._result = self._target(*self._args, **self._kwargs)
            except Exception as ex:
                if not isinstance(ex, (SystemExit, KeyboardInterrupt)):
                    import sys
                    import traceback

                    traceback.print_tb(*sys.exc_info())


class WaitingScreen(QWidget, Generic[_T]):
    def __init__(
        self,
        parent: QWidget | None,
        label: str | QWidget,
        target: Callable[..., _T] | None = None,
        args: Sequence[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
        margins: int | QMargins | None = None,
        label_alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
        cancellable: bool = True,
    ) -> None:
        super().__init__(
            parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )

        self.setWindowModality(Qt.WindowModality.WindowModal)

        def remove_html(s: str) -> str:
            if s.count(">") != s.count("<"):
                return s
            td: QTextDocument = QTextDocument(self)
            td.setHtml(s)
            return td.toPlainText()

        if isinstance(label, str):
            label = QLabel(label, self)
            label.setAlignment(label_alignment)
        if isinstance(label, QLabel):
            self.setWindowTitle(remove_html(label.text()))
        elif isinstance(label, QWidget):
            self.setWindowTitle(label.windowTitle())
        if not self.windowTitle():
            self.setWindowTitle(self.tr("Please wait…"))
        layout: QVBoxLayout = QVBoxLayout(self)
        spinner: QWidget | None = _spinner(self)
        if spinner is not None:
            layout.addWidget(spinner)
        layout.addWidget(label)
        if cancellable:
            cancel_button: QPushButton = QPushButton(self)
            cancel_button.setText(self.tr("&Cancel"))
            cancel_button.setShortcut(QKeySequence.StandardKey.Cancel)
            cancel_button.clicked.connect(self.stop)
            layout.addWidget(cancel_button)
            layout.setAlignment(cancel_button, Qt.AlignmentFlag.AlignCenter)

        if isinstance(margins, int):
            layout.setContentsMargins(margins, margins, margins, margins)
        elif isinstance(margins, QMargins):
            layout.setContentsMargins(margins)

        self._target: Callable[..., _T] | None = target
        self._args: Sequence[Any] = args
        self._kwargs: Mapping[str, Any] = kwargs or dict()
        self._thread: _Thread[_T] | None = None
        self._is_cancelled: bool = False

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def exec(self) -> _T | None:
        self._is_cancelled = False
        self._thread = _Thread(
            target=self._target,
            args=self._args,
            kwargs=self._kwargs,
        )
        self.show()
        self._thread.start()
        while self.active:
            QCoreApplication.processEvents()
            QCoreApplication.sendPostedEvents()
        if self._thread is not None:
            self._thread.join()
            self.hide()
            result: _T = self._thread.result()
            self._thread = None
            return result
        self.hide()
        return None

    def stop(self) -> None:
        if self.active:
            self._thread.join(0.0)
            self._thread = None
            self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled


if __name__ == "__main__":
    import sys
    from time import sleep

    from qtpy.QtCore import QTimer
    from qtpy.QtWidgets import QApplication, QWidget

    app: QApplication = QApplication(sys.argv)
    w: QWidget = QWidget()
    w.show()
    ws: WaitingScreen[None] = WaitingScreen(
        parent=w,
        label="label",
        target=sleep,
        args=(5,),
    )
    QTimer().singleShot(100, lambda: print(f"{ws.exec() = }"))
    app.exec()
