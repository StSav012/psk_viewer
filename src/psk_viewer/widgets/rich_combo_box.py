from qtpy.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
)
from qtpy.QtGui import (
    QAbstractTextDocumentLayout,
    QPaintEvent,
    QPainter,
    QPalette,
    QTextDocument,
)
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QStyle,
    QStyleOptionComboBox,
    QStyleOptionViewItem,
    QStylePainter,
    QStyledItemDelegate,
    QWidget,
)

__all__ = ["RichComboBox", "RichComboBoxDelegate"]

from psk_viewer.utils import the


class HTMLDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc: QTextDocument = QTextDocument(self)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        self.initStyleOption(option, index)
        style: QStyle | None = (
            option.widget.style() if option.widget else QApplication.style()
        )
        if style is None:
            raise RuntimeError("Failed to get style")
        with the(self._doc) as doc:
            doc.clear()
            doc.setHtml(option.text)
            option.text = ""
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter)
            ctx: QAbstractTextDocumentLayout.PaintContext = (
                QAbstractTextDocumentLayout.PaintContext()
            )
            if option.state & QStyle.StateFlag.State_Selected:
                ctx.palette.setBrush(
                    QPalette.ColorRole.Text, option.palette.highlightedText()
                )
            text_rect: QRect = style.subElementRect(
                QStyle.SubElement.SE_ItemViewItemText, option
            )
            painter.save()
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            painter.translate(text_rect.topLeft())
            painter.setClipRect(option.rect.translated(-text_rect.topLeft()))
            painter.translate(0, 0.5 * (option.rect.height() - doc.size().height()))
            doc.documentLayout().draw(painter, ctx)
            painter.restore()

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        options: QStyleOptionViewItem = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        with the(self._doc) as doc:
            doc.clear()
            doc.setHtml(options.text)
            doc.setTextWidth(options.rect.width())
            return QSize(
                round(doc.idealWidth()),
                round(QTextDocument().size().height()),
            )


class RichComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setItemDelegate(HTMLDelegate(self))
        self.view().setItemDelegate(HTMLDelegate(self))

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.currentIndex() >= 0 and (delegate := self.itemDelegate()) is not None:
            opt: QStyleOptionComboBox = QStyleOptionComboBox()
            self.initStyleOption(opt)
            option: QStyleOptionViewItem = QStyleOptionViewItem()
            option.rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox,
                opt,
                QStyle.SubControl.SC_ComboBoxEditField,
                self,
            )
            option.state = QStyle.StateFlag.State_Enabled
            if self.hasFocus():
                option.state |= QStyle.StateFlag.State_HasFocus
            option.text = self.currentText()
            option.displayAlignment = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            painter: QStylePainter = QStylePainter(self)
            painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
            painter.save()
            index = self.model().index(self.currentIndex(), 0)
            delegate.paint(painter, option, index)
            painter.restore()
        else:
            super().paintEvent(event)

    def setCurrentData(
        self,
        data: object,
        role: Qt.ItemDataRole = Qt.ItemDataRole.UserRole,
    ) -> None:
        for index in range(self.count()):
            if self.itemData(index, role) == data:
                self.setCurrentIndex(index)
                return
        self.setCurrentText("")


class RichComboBoxDelegate(HTMLDelegate):
    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        editor: RichComboBox = RichComboBox(parent)
        editor.addItem("", None)
        editor.setCurrentText(index.data(Qt.ItemDataRole.DisplayRole))
        if (candidates := index.data(Qt.ItemDataRole.BackgroundRole)) is not None:
            for text, data in candidates:
                editor.addItem(text, data)
            if (
                best_candidate := index.data(Qt.ItemDataRole.ForegroundRole)
            ) is not None:
                text, data = best_candidate
                editor.setCurrentData(data)
        return editor

    def setEditorData(
        self,
        editor: QWidget,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        if (
            isinstance(editor, RichComboBox)
            and (best_candidate := index.data(Qt.ItemDataRole.ForegroundRole))
            is not None
        ):
            text, data = best_candidate
            editor.setCurrentData(data)

    def setModelData(
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        if isinstance(editor, RichComboBox):
            model.setItemData(
                index,
                {
                    Qt.ItemDataRole.ForegroundRole: (
                        editor.currentText(),
                        editor.currentData(),
                    ),
                    Qt.ItemDataRole.DisplayRole: editor.currentText(),
                },
            )
