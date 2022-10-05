from PyQt5 import QtCore, QtGui


class StatusTipFilter(QtCore.QObject):
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(event, QtGui.QStatusTipEvent):
            return True
        return super().eventFilter(watched, event)