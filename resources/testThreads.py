# Qt imports
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QSize, QThread, QObject
from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QStyle, QWidget, QMenu, QAction, QStatusBar, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QApplication
import sys, time

class Camera(QObject):
    startedSignal = pyqtSignal()
    finishedSignal = pyqtSignal()
    errorSignal = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(Camera, self).__init__()
        print('Camera init',flush=True)

    def run(self):
        # self.startedSignal = pyqtSignal()
        # self.finishedSignal = pyqtSignal()
        # self.errorSignal = pyqtSignal(object)
        print('Camera running', flush=True)
        self.startedSignal.emit()
        counter = 5
        while (counter > 0):
            print(counter, flush=True)
            counter = counter - 1
        print('Trying to emit error', flush=True)
        self.errorSignal.emit('error signal from camera')
        print('Trying to emit finished', flush=True)
        self.finishedSignal.emit()
    
    @pyqtSlot()
    def quit(self):
        print('Camera quitting.',flush=True)
        


class DetectionManager(QObject):
    finishedSignal = pyqtSignal()
    error = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__()
        print('*** detection manager initialized.',flush=True)

    def run(self):
        print('*** detection manager running.',flush=True)
        self.threadCount = 1
        # while(self.threadCount<5):
        print('Starting camera',flush=True)
        self.camera = Camera()
        self.cameraThread = QThread()
        self.camera.moveToThread(self.cameraThread)
        self.camera.errorSignal.connect(self.passError)
        self.cameraThread.started.connect(self.camera.run)
        self.camera.finishedSignal.connect(self.threadComplete)
        self.camera.finishedSignal.connect(self.cameraThread.quit)
        self.camera.finishedSignal.connect(self.deleteLater)
        self.camera.startedSignal.connect(self.cameraStarted)
        self.cameraThread.finished.connect(self.cameraThread.deleteLater)
        self.cameraThread.start()

            # self.threadCount = self.threadCount+1
        while(self.cameraThread.isRunning()):
            print('Sleeping..')
            time.sleep(1)
        self.finishedSignal.emit()
        print('*** detection manager complete.',flush=True)

    @pyqtSlot(object)
    def passError(self, message):
        print('Detection Manager passError got: ', message, flush=True )
        self.error.emit(message)
    
    @pyqtSlot()
    def cameraStarted(self):
        print('************* Camera has been started.',flush=True)

    @pyqtSlot()
    def threadComplete(self):
        print('Thread counter: ', self.threadCount,flush=True)

class App(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('testing threads')
        screen = QDesktopWidget().availableGeometry()
        self.setGeometry(QStyle.alignedRect(Qt.LeftToRight,Qt.AlignHCenter,QSize(800,600),screen))
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        appScreen = self.frameGeometry()
        appScreen.moveCenter(screen.center())
        self.move(appScreen.topLeft())
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.containerLayout = QVBoxLayout()
        self.containerLayout.setSpacing(8)
        self.centralWidget.setLayout(self.containerLayout)
        self.button = QPushButton('Start threads.')
        self.button.clicked.connect(self.startThreads)
        self.containerLayout.addWidget(self.button)
    
    def startThreads(self):
        print('Starting threads sequence..')
        self.detect = DetectionManager()
        self.detectThread = QThread()
        self.detect.moveToThread(self.detectThread)
        self.detectThread.started.connect(self.detect.run)
        self.detect.finishedSignal.connect(self.detectThread.quit)
        self.detect.finishedSignal.connect(self.detect.deleteLater)
        self.detectThread.finished.connect(self.detectThread.deleteLater)
        self.detectThread.start()

if __name__=='__main__':
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec_())