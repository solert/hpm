import datetime as dt
import pandas as pd
from PySide2.QtWidgets import (
    QWidget,
    QTableWidget,
    QHeaderView,
    QHBoxLayout,
    QToolButton,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QStyledItemDelegate,
    QFileDialog,
    QDateEdit,
    QProgressBar,
    QTableWidgetItem,
    QMenu,
    QAction,
)
from PySide2.QtCore import Qt, QDate
from PySide2.QtGui import QIcon, QPixmap
from typing import Callable, List


# Constant
STANDARD_PADDING = 30


def setWidthFromString(widget: QWidget, string: str, padding: bool = True) -> None:
    """
    Update the width of a QWidget based on a string size

    NB: the widget must have access to the following methods -> self.fontMetrics().boundingRect(string).width()
    """
    if padding:
        width = widget.fontMetrics().boundingRect(string).width() + STANDARD_PADDING
    else:
        width = widget.fontMetrics().boundingRect(string).width()
    widget.setFixedWidth(width)


def build_icon_from_path(path: str, target_button: QToolButton = None) -> QIcon:
    """
    Return a QIcon from a path and set it to a button if provided
    """
    pixmap = QPixmap(path)
    icon = QIcon(pixmap)
    if target_button is not None:
        target_button.setIcon(icon)
    return icon


def remove_widget_cleanly_at(index: int, layout) -> None:
    widget = layout.itemAt(index).widget()
    layout.removeWidget(widget)
    # removeWidget seems equivalent to takeAt : remove widget from layout list but do not delete it
    # widget.deleteLater() (destruction on C++ side) : delete the widget but do not remove it from layout list -> need removeWidget or takeAt
    widget.setParent(None)  # Seem to be equivalent to both precedent methods cumulated


class CustomTable(QTableWidget):
    """
    Interesting notions:
    - Set a default width/height to columns/rows -> self.table.horizontalHeader().setDefaultSectionSize(width) / self.table.verticalHeader().setDefaultSectionSize(height)
    - One could have directly overridden the contextMenuEvent method instead of activating et connecting the customContextMenuRequested signal
    """

    def __init__(
        self,
        parent: QWidget = None,
        df: pd.DataFrame = None,
        add_icon_path: str = None,
        remove_icon_path: str = None,
    ) -> None:
        super().__init__(parent)
        self.columns = []
        self.add_icon_path = add_icon_path
        self.remove_icon_path = remove_icon_path

        # Resize the table to its content dynamically
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )  # QHeaderView.Stretch to fill space perfectly
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Fill the table from a df
        if df is not None:
            self.fill(df)

        # Activate customContextMenuRequested signal for any event of the context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # Connect to a method that displays a custom context menu
        self.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos))

    def to_df(self) -> pd.DataFrame:
        """
        Export QTableWidget to a pandas Dataframe
        """
        nb_rows, nb_columns = self.rowCount(), self.columnCount()
        columns = [self.horizontalHeaderItem(j).text() for j in range(nb_columns)]

        table_dict = {column_name: [self.item(i, j) for i in range(nb_rows)] for j, column_name in enumerate(columns)}
        str_dict = {
            column_name: [table_item.text() if table_item is not None else "" for table_item in table_dict[column_name]]
            for column_name in table_dict
        }
        df = pd.DataFrame(str_dict)

        # Keep column order
        return df[columns]

    def fill(self, df: pd.DataFrame) -> None:
        """
        Fill the table from a pandas Dataframe
        """
        nb_rows, nb_columns = df.shape
        self.setRowCount(nb_rows)
        self.setColumnCount(nb_columns)
        self.columns = list(df.columns)
        self.setHorizontalHeaderLabels(self.columns)

        for i in range(nb_rows):
            for j in range(nb_columns):
                item = df.iloc[i, j]
                table_item = QTableWidgetItem(item)
                self.setItem(i, j, table_item)

    def add_row(self) -> None:
        """
        Insert a row at the end of the table
        """
        self.insertRow(self.rowCount())

    @staticmethod
    def create_action(text: str, f: Callable, icon_path: str = None) -> QAction:
        """
        Create a custom action for a context menu
        """
        if icon_path:
            icon = build_icon_from_path(icon_path)
            action = QAction(text, icon=icon)
        else:
            action = QAction(text)
        action.triggered.connect(f)

        return action

    def show_context_menu(self, pos) -> None:
        idx = self.indexAt(pos)
        if idx.isValid():
            row_idx = idx.row()

            # Create context menu and custom actions
            context_menu = QMenu(parent=self)
            add_row_action = self.create_action(
                "Insérer une ligne",
                lambda *args: self.insertRow(row_idx),
                self.add_icon_path,
            )
            remove_row_action = self.create_action(
                "Supprimer la ligne",
                lambda *args: self.removeRow(row_idx),
                self.remove_icon_path,
            )

            for action in [add_row_action, remove_row_action]:
                context_menu.addAction(action)

            # Display context menu
            context_menu.exec_(self.mapToGlobal(pos))


class CustomDelegate(QStyledItemDelegate):
    """
    Class that overrides the updateEditorGeometry method
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        editor.resize(
            max(editor.sizeHint().width(), option.rect.width()), editor.height()
        )  # NB: option.rect returns the cell rectangle
        rect = editor.geometry()
        parentRect = editor.parent().rect()
        # 'If' statements are here to ensure that the editor is fully visible in the view, which is extremely important when the item is not fully visible due to scrolling
        if not parentRect.contains(rect):
            if rect.right() > parentRect.right():
                rect.moveRight(parentRect.right())
            if rect.x() < parentRect.x():
                rect.moveLeft(parentRect.x())
            if rect.bottom() > parentRect.bottom():
                rect.moveBottom(parentRect.bottom())
            if rect.y() < parentRect.y():
                rect.moveTop(parentRect.y())
            editor.setGeometry(rect)


class PathSelectionDelegate(CustomDelegate):
    """
    Class allowing to customize the editor (QToolButton + QLineEdit) of a table items

    Interesting notions:
    - Edit the recommended size of the table cell/item so that it is equal to the editor recommended size: index.model().setData(index, editor.sizeHint(), Qt.SizeHintRole)
    - Edit the rectangle size manually: option.rect.setSize(...)
    - Insert a widget in a cell without delegate: table.setCellWidget(row_id, column_id, widget)
    """

    def __init__(self, parent: QWidget, folder_icon_path: str, path_selection_type: str = "file"):
        super().__init__(parent)
        self.folder_icon_path = folder_icon_path
        self.set_path_selection_type(path_selection_type)

    def createEditor(self, parent: QWidget, option, index) -> QWidget:
        editor = QWidget(parent)

        # Fill the editor background with white to hide the item value
        editor.setAutoFillBackground(True)
        editor_hlayout = QHBoxLayout(editor)

        # Delete editor_hlayout margins to optimize space
        editor_hlayout.setContentsMargins(0, 0, 0, 0)

        # Minimize space between the button and the line_edit
        editor_hlayout.setSpacing(1)

        folder_button = QToolButton()
        self.folder_button_clicked = False
        # folder_button.setStyleSheet("border: none;")  # To delete the button borders
        build_icon_from_path(self.folder_icon_path, target_button=folder_button)
        editor.line_edit = QLineEdit(frame=False)
        folder_button.clicked.connect(lambda *args: self.add_path(editor.line_edit))

        # Transfer the line edit focus to the editor (so that the eventFilter method is called and handles the FocusOut event)
        editor.line_edit.setFocusProxy(editor)
        editor_hlayout.addWidget(folder_button)
        editor_hlayout.addWidget(editor.line_edit)
        return editor

    def setEditorData(self, editor, index) -> None:
        model_data = index.model().data(index, Qt.EditRole)
        editor.line_edit.setText(model_data)  # Set line_edit value

    def setModelData(self, editor, model, index) -> None:
        editor_data = editor.line_edit.text()  # Get line_edit value
        model.setData(index, editor_data, Qt.EditRole)

    def eventFilter(self, editor, event):
        if event.type() in (
            event.FocusIn,
            event.KeyPress,
            event.KeyRelease,
            event.ShortcutOverride,
            event.InputMethod,
            event.ContextMenu,
        ):
            if event.type() in (
                event.KeyPress,
                event.KeyRelease,
                event.ShortcutOverride,
            ) and event.key() in (
                Qt.Key_Tab,
                Qt.Key_Backtab,
                Qt.Key_Enter,
                Qt.Key_Return,
                Qt.Key_Escape,
            ):
                return super().eventFilter(editor, event)
            editor.line_edit.event(event)
            return event.isAccepted()
        if event.type() == event.FocusOut and self.folder_button_clicked:
            return event.isAccepted()

        return super().eventFilter(editor, event)

    def set_path_selection_type(self, path_selection_type: str) -> None:
        self.path_selection_type = path_selection_type

    def add_path(self, line_edit: QLineEdit) -> None:
        """
        Open the file manager et get the selected folder/file path
        """
        self.folder_button_clicked = True

        if self.path_selection_type == "folder":
            path = QFileDialog.getExistingDirectory(None, "Sélectionner un dossier")
        elif self.path_selection_type == "file":
            path = QFileDialog.getOpenFileName(None, "Sélectionner un fichier de prix")[0]
        else:
            raise ValueError("Le type de sélection des chemins n'est pas valide")

        if path:
            line_edit.setText(path)

        self.folder_button_clicked = False


class ComboBoxDelegate(CustomDelegate):
    """
    Class allowing to customize the editor (QComboBox) of a table items
    """

    def __init__(self, parent, header: str = None, items: List[str] = None):
        super().__init__(parent)
        self.header = header
        self.items = items

    def createEditor(self, parent, option, index) -> QComboBox:
        editor = QComboBox(parent)
        editor.setAutoFillBackground(True)
        if self.header:
            editor.addItem(self.header)
            editor.insertSeparator(1)
        if self.items:
            editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index) -> None:
        model_data = index.model().data(index, Qt.EditRole)
        # Necessary condition from the insertion of the separator because the empty string matches the latter (and we do not want it to)
        # Cf the doc, if the combobox is not editable, setCurrentText select the first item that matches the provided text
        # One also could have written the following:
        # matching_index = editor.findText(model_data)
        # if matching_index != -1:
        # 	editor.setCurrentIndex(matching_index)
        if model_data in self.items:
            editor.setCurrentText(model_data)

    def setModelData(self, editor, model, index) -> None:
        editor_data = editor.currentText()
        if editor_data == self.header:
            model.setData(index, "", Qt.EditRole)
        else:
            model.setData(index, editor_data, Qt.EditRole)


class CustomDateEdit(QDateEdit):
    """
    QDateEdit class with calendarPopUp activation
    """

    def __init__(self, date_min: dt.date = None) -> None:
        super().__init__()
        self.setCalendarPopup(True)
        self.setDisplayFormat("d MMMM yyyy")
        self.attached_cal = self.calendarWidget()
        self.attached_cal.setGridVisible(True)
        if date_min is not None:
            self.setMinimumDate(QDate(date_min.year, date_min.month, date_min.day))
        # calendar_format = QTextCharFormat()
        # calendar_format.setFontWeight(QFont.Bold)
        # attached_cal.setHeaderTextFormat(calendar_format)

    # Override the resizeEvent method to modify, as soon as the width of the object changes, the width of its associated calendar
    # def resizeEvent(self, event):
    # 	width = self.width()
    # 	if width > 273:   #273 is the min size (imho) for which the calendar displays without truncation
    # 		self.attached_cal.setFixedWidth(width)
    # 	elif self.attached_cal.width() != 273:
    # 		self.attached_cal.setFixedWidth(273)
    # 	super().resizeEvent(event)


class CustomLabel(QLabel):
    def __init__(self, fixed_width: int, word_wrap: bool = None, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(fixed_width)
        if word_wrap:
            self.setWordWrap(word_wrap)  # Go to new line if message is too long


class CustomButton:
    """
    Code for customizing button classes
    Warning: it is not intended to be called directly -> error
    """

    def __init__(
        self, text: str = "", action: Callable = lambda: None, tooltip: str = "", icon_path: str = None
    ) -> None:
        self.setText(text)
        width = self.fontMetrics().boundingRect(text).width() + STANDARD_PADDING
        self.setMaximumWidth(width)
        self.clicked.connect(action)
        if tooltip:
            self.setToolTip(tooltip)
        if icon_path:
            build_icon_from_path(icon_path, target_button=self)


class CustomPushButton(QPushButton, CustomButton):
    def __init__(
        self,
        text: str = "",
        action: Callable = lambda: None,
        tooltip: str = "",
        icon_path: str = None,
        parent: QWidget = None,
    ) -> None:
        QPushButton.__init__(self, parent)
        CustomButton.__init__(self, text, action, tooltip, icon_path)


class CustomToolButton(QToolButton, CustomButton):
    def __init__(
        self,
        text: str = "",
        action: Callable = lambda: None,
        tooltip: str = "",
        icon_path: str = None,
        parent: QWidget = None,
    ) -> None:
        QToolButton.__init__(self, parent)
        CustomButton.__init__(self, text, action, tooltip, icon_path)


class CustomProgressBar(QProgressBar):
    def __init__(self, range_: tuple, alignment: Qt.Alignment = None, parent: QWidget = None) -> None:
        super().__init__()
        self.setRange(range_[0], range_[1])
        if alignment is not None:
            self.setAlignment(alignment)
