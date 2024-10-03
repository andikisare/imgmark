from PyQt6.QtWidgets import ( QApplication, QMainWindow, QPushButton,
                              QLabel, QScrollArea, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                              QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QInputDialog, QCheckBox, 
                              QSlider, QFrame, QLineEdit, QSizePolicy )
from PyQt6.QtGui import QPixmap, QCursor, QAction, QIcon, QFont, QPainter
from PyQt6.QtCore import Qt, QEvent, QPoint
from galmark.mark import Mark
from galmark import __dirname__, __icon__, __heart_solid__, __heart_clear__
import galmark.io
import sys
import os
import datetime as dt
import textwrap
from math import floor, inf
from functools import partial
from PIL import Image
from PIL.ImageQt import ImageQt
from PIL.ImageFilter import GaussianBlur
from PIL.ImageEnhance import Contrast, Brightness

class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Raised)

class PosWidget(QWidget):
    """
    This window displays the instructions and keymappings
    """
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(__icon__))
        layout = QHBoxLayout()
        self.fullw = self.screen().size().width()
        self.fullh = self.screen().size().height()
        self.setWindowTitle('Instructions')
        self.setLayout(layout)
        
        # pix text 
        self.x_text = QLineEdit()
        self._text_setup(self.x_text)
        self.y_text = QLineEdit()
        self._text_setup(self.y_text)

        self.pix_label = QLabel()
        self._label_setup(self.pix_label,'Pixel:')

        # wcs text 
        self.ra_text = QLineEdit()
        self._text_setup(self.ra_text)
        self.dec_text = QLineEdit()
        self._text_setup(self.dec_text)

        self.wcs_label = QLabel()
        self._label_setup(self.wcs_label,'WCS:')

        # Add widgets to layout
        layout.addStretch(1)
        layout.addWidget(self.pix_label)
        layout.addWidget(self.x_text)
        layout.addWidget(self.y_text)
        layout.addWidget(self.wcs_label)
        layout.addWidget(self.ra_text)
        layout.addWidget(self.dec_text)
        layout.addStretch(1)

    def _text_setup(self,widget:QLineEdit):
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setReadOnly(True)
        widget.setFixedHeight(30)
        widget.setFixedWidth(100)
        widget.setSizePolicy(*[QSizePolicy.Policy.Fixed]*2)

    def _label_setup(self,label:QLabel,text:str):
        label.setText(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFixedHeight(30)

class AdjustmentsWindow(QWidget):
    """
    Blur window
    """
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(__icon__))
        layout = QVBoxLayout()
        self.fullw = self.screen().size().width()
        self.fullh = self.screen().size().height()
        self.setWindowTitle('Brightness and Contrast')
        self.setLayout(layout)

        # Brightness slider
        self.brightnessSlider = QSlider()
        self._slider_setup(self.brightnessSlider,self.onBrightnessMoved)

        self.brightnessLabel = QLabel()
        self.brightnessLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brightnessLabel.setText(f'Brightness: {self.brightnessSlider.value()}')

        # Contrast slider
        self.contrastSlider = QSlider()
        self._slider_setup(self.contrastSlider,self.onContrastMoved)

        self.contrastLabel = QLabel()
        self.contrastLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contrastLabel.setText(f'Contrast: {self.contrastSlider.value()}')

        layout.addWidget(self.brightnessLabel)
        layout.addWidget(self.brightnessSlider)
        layout.addWidget(self.contrastLabel)
        layout.addWidget(self.contrastSlider)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setFixedWidth(int(self.fullw/6))
        self.setFixedHeight(layout.sizeHint().height())

        # Set position of window
        qt_rectangle = self.frameGeometry()
        center_point = QApplication.primaryScreen().geometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

    def _slider_setup(self,slider:QSlider,connect):
        slider.setMinimum(-10)
        slider.setMaximum(10)
        slider.setValue(0)
        slider.setOrientation(Qt.Orientation.Horizontal)
        slider.sliderMoved.connect(connect)

    def onBrightnessMoved(self,pos):
        self.brightnessSlider.setValue(floor(pos))
        self.brightnessLabel.setText(f'Brightness: {floor(self.brightnessSlider.value())/10}')
    
    def onContrastMoved(self,pos):
        self.contrastSlider.setValue(floor(pos))
        self.contrastLabel.setText(f'Contrast: {floor(self.contrastSlider.value())/10}')

    def show(self):
        super().show()
        self.activateWindow()   

class BlurWindow(QWidget):
    """
    Blur window
    """
    def __init__(self):
        super().__init__()
        
        self.setWindowIcon(QIcon(__icon__))
        layout = QVBoxLayout()
        self.fullw = self.screen().size().width()
        self.fullh = self.screen().size().height()
        self.setWindowTitle('Gaussian Blur')
        self.setLayout(layout)

        max_blur = int((self.fullw+self.fullh)/20)
        self.slider = QSlider()
        self.slider.setMinimum(0)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(self.onSliderMoved) 

        self.valueLabel = QLabel()
        self.valueLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.valueLabel.setText(f'Radius: {self.slider.value()}')

        layout.addWidget(self.valueLabel)
        layout.addWidget(self.slider)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(int(self.fullw/6))
        self.setFixedHeight(layout.sizeHint().height())

        # Set position of window
        qt_rectangle = self.frameGeometry()
        center_point = QApplication.primaryScreen().geometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

    def onSliderMoved(self, pos):
        self.slider.setValue(floor(pos))
        self.valueLabel.setText(f'Radius: {floor(self.slider.value())/10}')

    def show(self):
        super().show()
        self.activateWindow()

class ImageFilters():
    def __init__(self,img:Image.Image,a=1,b=1,r=0):
        self.a = a
        self.b = b
        self.r = r
        self.img = img
    
    def setA(self,a): self.a = a
    def setB(self,b): self.a = b
    def setR(self,r): self.a = r

    def apply(self) -> Image.Image:
        def blur(img:Image.Image):
            return img.filter(GaussianBlur(self.r))
        def brighten(img:Image.Image):
            return Brightness(img).enhance(self.a)
        def contrast(img:Image.Image):
            return Contrast(img).enhance(self.b)
        return contrast(brighten(blur(self.img)))

class InstructionsWindow(QWidget):
    """
    This window displays the instructions and keymappings
    """
    def __init__(self,groupNames):
        super().__init__()
        self.setWindowIcon(QIcon(__icon__))
        layout = QVBoxLayout()
        self.fullw = self.screen().size().width()
        self.fullh = self.screen().size().height()
        self.setWindowTitle('Instructions')
        self.setLayout(layout)
        
        # Create the scroll area and label
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.label = QLabel()
        self.scroll_area.setWidget(self.label)
        self.scroll_area.setWidgetResizable(True)
        font = QFont('Courier')
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Lists for keybindings
        actions_list = ['Next','Back','Delete','Enter comment', 'Focus', 'Zoom in/out', 'Exit', 'Help']
        group_list = [f'Group \"{group}\"' for group in groupNames[1:]]
        actions_list = group_list + actions_list
        buttons_list = ['Left click OR 1', '2', '3', '4', '5', '6', '7', '8', '9', 'Tab', 'Shift+Tab', 'Right click OR Backspace', 'Enter', 'Middle click', 'Scroll wheel', 'Esc OR Q', 'F1', ]

        # Determing widths for keybindings list
        actions_width = max([len(a) for a in actions_list])
        buttons_width = max([len(b) for b in buttons_list]) + 10
        fullw_text = actions_width + buttons_width

        # Create text
        text = 'ALL data is saved when pressing "Next," "Back," or "Enter" in the window, as well as checking a category, exiting, or making a mark.'
        text = textwrap.wrap(text, width=fullw_text)
        text = '\n'.join([f'{l:<{fullw_text}}' for l in text]) + '\n'
        text += '-'*(fullw_text) + '\n'
        text += f'{'Keybindings':^{fullw_text}}\n'
        text += '-'*(fullw_text) + '\n'
        for i in range(0,len(actions_list)):
            text += f'{actions_list[i]:.<{actions_width}}{buttons_list[i]:.>{buttons_width}}\n'
        self.label.setText(text)
        text.removesuffix('\n')

        # Add scroll area to layout, get size of layout
        layout.addWidget(self.scroll_area)
        layout_width, layout_height = layout.sizeHint().width(), layout.sizeHint().height()

        # Resize window according to size of layout
        self.resize(int(layout_width*1.1),int(layout_height*1.1))

    def show(self):
        super().show()
        self.activateWindow()

class StartupWindow(QInputDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(__icon__))
        qt_rectangle = self.frameGeometry()
        center_point = QApplication.primaryScreen().geometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

    def getUser(self) -> None:
        # Make popup to get name
        text, OK = self.getText(self,"Startup", "Enter a username (no caps, no space, e.g. ryanwalker)")

        if OK: return text
        else: sys.exit()

class MainWindow(QMainWindow):
    def __init__(self, username:str, out_dir:str, image_dir:str, group_names:list[str], category_names:list[str], group_max:int, imtype:str = 'tif'):
        '''
        Constructor

        Required Inputs:
            main (Tk): root to which the tkinter widgets are added

        Optional Inputs:
            path (string): path to directory containing candidate images
            imtype (string): file extension of images to be ranked
            outfile (string): filename of text file for saving data
        '''
        super().__init__()
        self.setWindowTitle("Galaxy Marker")
        self.setWindowIcon(QIcon(__icon__))
        self.fullw = self.screen().size().width()
        self.fullh = self.screen().size().height()

        # Filter windows
        self.blurWindow = BlurWindow()
        self.blurWindow.slider.valueChanged.connect(self.onBlur)
        self.adjustmentsWindow = AdjustmentsWindow()
        self.adjustmentsWindow.contrastSlider.valueChanged.connect(self.onContrast)
        self.adjustmentsWindow.brightnessSlider.valueChanged.connect(self.onBrighten)
        
        ### Default adjustment values
        self.r = 0
        self.a = 1
        self.b = 1

        # Initialize config
        self.config = 'galmark.cfg'
        self.username, self.group_names, self.category_names, self.group_max = username, group_names, category_names, group_max
        self.date = dt.datetime.now(dt.UTC).date().isoformat()

        # Initialize output dictionary
        self.data = galmark.io.load(username)

        # Find all images in image directory
        self.imtype = imtype
        self.image_paths, self.idx = galmark.io.glob(image_dir,self.imtype,data_filt=self.data)
        self.N = len(self.image_paths)

        try: self.image = Image.open(self.image_paths[self.idx])
        except:
            print('No images found. Please specify image directory in configuration file (galmark.cfg) and try again.')
            sys.exit()

        self.qimage = ImageQt(self.image)

        # Set max blur based on size of image
        blur_max = int((self.qimage.height()+self.qimage.width())/20)
        self.blurWindow.slider.setMaximum(blur_max)

        self.image_file = self.image.filename.split(os.sep)[-1]
        self.wcs = galmark.io.parseWCS(self.image)

        # Current image widget
        self.image_label = QLabel(f'{self.image_file} ({self.idx+1} of {self.N})')
        self.image_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Mouse position widget
        self.pos_widget = PosWidget()

        # Create image view
        self.image_scene = QGraphicsScene(self)
        self.pixmap = self._pixmap()
        
        

        self._pixmap_item = QGraphicsPixmapItem(self.pixmap)

        self.image_scene.addItem(self._pixmap_item)
        
        self.image_view = QGraphicsView(self.image_scene)       
        
        ### Disable scrollbar
        self.image_view.verticalScrollBar().blockSignals(True)
        self.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.image_view.horizontalScrollBar().blockSignals(True)
        self.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        ### Image view position setup and mouse tracking
        self.image_view.move(0, 0)
        self.image_view.setTransformationAnchor(self.image_view.ViewportAnchor(1))
        self.image_view.setMouseTracking(True)
        self.image_view.mouseMoveEvent = self.mouseMoveEvent

        ### Install event filters
        self.image_view.viewport().installEventFilter(self)

        # Back widget
        self.back_button = QPushButton(text='Back',parent=self)
        self.back_button.setFixedHeight(40)
        self.back_button.clicked.connect(self.onBack)
        self.back_button.setShortcut('Shift+Tab')

        # Enter Button
        self.submit_button = QPushButton(text='Enter',parent=self)
        self.submit_button.setFixedHeight(40)
        self.submit_button.clicked.connect(self.onEnter)
        self.submit_button.setShortcut('Return')

        # Next widget
        self.next_button = QPushButton(text='Next',parent=self)
        self.next_button.setFixedHeight(40)
        self.next_button.clicked.connect(self.onNext)
        self.next_button.setShortcut('Tab')

        # Comment widget
        self.comment_box = QLineEdit(parent=self)
        self.comment_box.setFixedHeight(40)
    
        # Botton Bar layout
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addWidget(self.back_button)
        self.bottom_layout.addWidget(self.next_button)
        self.bottom_layout.addWidget(self.comment_box)
        self.bottom_layout.addWidget(self.submit_button)
        
        ### Category widgets
        self.categories_layout = QHBoxLayout()

        # Category boxes
        self.category_boxes = [QCheckBox(text=self.category_names[i], parent=self) for i in range(1,6)]
        for i, box in enumerate(self.category_boxes):
            box.setFixedHeight(20)
            box.setStyleSheet("margin-left:30%; margin-right:30%;")
            box.clicked.connect(partial(self.onCategory,i+1))
            self.categories_layout.addWidget(box)

        # Favorite box
        self.favorite_file_list = galmark.io.load_fav(username)
        self.favorite_box = QCheckBox(parent=self)
        self.favorite_box.setFixedHeight(20)
        self.favorite_box.setFixedWidth(40)
        self.favorite_box.setIcon(QIcon(__heart_clear__))
        self.favorite_box.setTristate(False)
        self.favorite_box.clicked.connect(self.onFavorite)
        self.categories_layout.addWidget(self.favorite_box)
        self.favorite_box.setShortcut('F')

        # Add widgets to main layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.image_label)
        layout.addWidget(self.image_view)
        layout.addWidget(self.pos_widget)
        layout.addWidget(self.hsep())
        layout.addLayout(self.bottom_layout)
        layout.addLayout(self.categories_layout)
        self.setCentralWidget(central_widget)
        
        # Menu bar
        menuBar = self.menuBar()

        ## File menu
        fileMenu = menuBar.addMenu("&File")

        ### Exit menu
        exitMenu = QAction('&Exit', self)
        exitMenu.setShortcuts(['Esc','q'])
        exitMenu.setStatusTip('Exit')
        exitMenu.triggered.connect(self.closeEvent)
        fileMenu.addAction(exitMenu)

        ## Filter menu
        filterMenu = menuBar.addMenu("&Filters")

        ### Blur
        blurMenu = QAction('&Gaussian Blur...',self)
        blurMenu.setStatusTip("Gaussian Blur")
        blurMenu.setShortcuts(['Ctrl+b'])
        blurMenu.triggered.connect(self.blurWindow.show)
        filterMenu.addAction(blurMenu)

        ### Brightness and Contrast
        adjustMenu = QAction('&Brightness and Contrast...',self)
        adjustMenu.setStatusTip("Brightness and Contrast")
        adjustMenu.setShortcuts(['Ctrl+a'])
        adjustMenu.triggered.connect(self.adjustmentsWindow.show)
        filterMenu.addAction(adjustMenu)

        ## Help menu
        helpMenu = menuBar.addMenu('&Help')

        ### Instructions and Keymapping window
        self.instructionsWindow = InstructionsWindow(self.group_names)
        instructionsMenu = QAction('&Instructions', self)
        instructionsMenu.setShortcuts(['F1'])
        instructionsMenu.setStatusTip('Instructions')
        instructionsMenu.triggered.connect(self.instructionsWindow.show)
        helpMenu.addAction(instructionsMenu)
        
        # Resize and center MainWindow; move instructions off to the right
        self.resize(int(self.fullw/2.5),int(self.fullw/2.5))


        center = QApplication.primaryScreen().geometry().center()
        rect_topleft = (center.x()-int(self.width()/2), 
                        center.y()-int(self.height()/2))
        self.move(*rect_topleft)

        self.instructionsWindow.move(int(self.x()+self.width()*1.04),self.y())
        self.instructionsWindow.show()

        # Initialize some data
        self.getComment()
        self.markUpdate()
        self.categoryUpdate()

        
        
    def _pixmap(self):
        pixmap_base = QPixmap.fromImage(self.qimage)

        w, h = pixmap_base.height(), pixmap_base.width()
        _x, _y = int(w*4), int(h*4)

        pixmap = QPixmap(w*9,h*9)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.drawPixmap(_x, _y, pixmap_base)
        painter.end()

        return pixmap

    def hsep(self) -> QHLine:
        hline = QHLine()
        hline.setLineWidth(0)
        hline.setMidLineWidth(1)
        hline.setMinimumHeight(1)
        return hline

    def eventFilter(self, source, event):
        # Event filter for zooming without scrolling
        if (source == self.image_view.viewport()) and (event.type() == 31):
            x = event.angleDelta().y() / 120
            if x > 0:
                self.zoom(-1)
            elif x < 0:
                self.zoom()
            return True

        return super().eventFilter(source, event)
    
    # === Events ===

    def resizeEvent(self, event):
        '''
        Resize event; rescales image to fit in window, but keeps aspect ratio
        '''
        transform = self.image_view.transform()
        self.image_view.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_view.setTransform(transform)
        super().resizeEvent(event)

    def keyPressEvent(self,event):
        # Check if key is bound with marking the image
        markButtons = galmark.io.markBindingCheck(event)
        for i in range(0,9):
            if markButtons[i]: self.onMark(group=i+1)

        if (event.key() == Qt.Key.Key_Backspace) or (event.key() == Qt.Key.Key_Delete):
            self.getSelectedMarks()

    def mousePressEvent(self,event):
        # Check if key is bound with marking the image
        markButtons = galmark.io.markBindingCheck(event)
        for i in range(0,9):
            if markButtons[i]: self.onMark(group=i+1)
        
        if (event.button() == Qt.MouseButton.MiddleButton):
            self.onMiddleMouse()

        if (event.button() == Qt.MouseButton.RightButton):
            self.getSelectedMarks()

    def mouseMoveEvent(self, event):
        # Mark if hovering over image
        ep, lp = self.mouseImagePos()
        lp_true = lp - 4*QPoint(self.image.width,self.image.height)
        x, y = lp_true.x(), lp_true.y()

        if (x>=0) and (x<=self.image.width) and (y>=0) and  (y<=self.image.height):
            h, w = self.wcs._naxis
            _x, _y = x, self.image.height - y

            ra, dec = self.wcs.all_pix2world([[_x, _y]], 0)[0]

            self.pos_widget.x_text.setText(f'{x}')
            self.pos_widget.y_text.setText(f'{y}')

            self.pos_widget.ra_text.setText(f'{ra:.4f}°')
            self.pos_widget.dec_text.setText(f'{dec:.4f}°')

        else:
            self.pos_widget.x_text.setText('')
            self.pos_widget.y_text.setText('')

            self.pos_widget.ra_text.setText('')
            self.pos_widget.dec_text.setText('')
    
    # === On-actions ===
    
    def onFavorite(self,state):
        state = Qt.CheckState(state)
        if state == Qt.CheckState.PartiallyChecked:
            self.favorite_box.setIcon(QIcon(__heart_solid__))
            self.favorite_file_list.append(self.image_file)
            galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)
        else:
            self.favorite_box.setIcon(QIcon(__heart_clear__))
            try:
                self.favorite_file_list.remove(self.image_file)
            except: pass
            galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)

    def onCategory(self,i:int) -> None:
        if (self.category_boxes[i-1].checkState() == Qt.CheckState.Checked) and (i not in self.data[self.image_file]['categories']):
            self.data[self.image_file]['categories'].append(i)
        elif (i in self.data[self.image_file]['categories']):
            self.data[self.image_file]['categories'].remove(i)
        galmark.io.save(self.data,self.username,self.date)
        galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)

    def onMark(self, group:int=0) -> None:
        '''
        Actions to complete when marking
        '''

        # get event position and position on image
        ep, lp = self.mouseImagePos()
        lp_true = lp - 4*QPoint(self.image.width,self.image.height)
        x, y = lp_true.x(), lp_true.y()
        
        # Mark if hovering over image
        if self.group_max[group - 1] == 'None': limit = inf
        else: limit = int(self.group_max[group - 1])

        if (x>=0) and (x<=self.image.width) and (y>=0) and  (y<=self.image.height):
            mark = Mark(lp.x(),lp.y(),wcs=self.wcs,group=group)
            mark.draw(self.image_scene)

            if (limit == 1) and (len(self.data[self.image_file][group]['marks']) == 1):
                prev_mark = self.data[self.image_file][group]['marks'][0]
                self.image_scene.removeItem(prev_mark)
                self.data[self.image_file][group]['marks'][0] = mark

            elif (len(self.data[self.image_file][group]['marks']) < limit):
                if not self.data[self.image_file][group]['marks']:
                    self.data[self.image_file][group]['marks'] = []

                self.data[self.image_file][group]['marks'].append(mark)

            galmark.io.save(self.data,self.username,self.date)
            galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)

    def onNext(self):
        if self.idx+1 < self.N:
            # Increment the index
            self.idx += 1
            self.commentUpdate()
            self.imageUpdate()
            self.markUpdate()
            self.getComment()
            self.categoryUpdate()
            self.favoriteUpdate()
            # galmark.io.save(self.data,self.username,self.date)

    def onBack(self):
        if self.idx+1 > 1:
            # Increment the index
            self.idx -= 1
            self.commentUpdate()
            self.imageUpdate()
            self.markUpdate()
            self.getComment()
            self.categoryUpdate()
            self.favoriteUpdate()
            # galmark.io.save(self.data,self.username,self.date)
            
    def onEnter(self):
        self.commentUpdate()
        self.comment_box.clearFocus()
        galmark.io.save(self.data,self.username,self.date)
        galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)
    
    def closeEvent(self, event):
        self.commentUpdate()
        sys.exit()

    def onMiddleMouse(self):
        # Center on cursor
        center = self.image_view.viewport().rect().center()
        scene_center = self.image_view.mapToScene(center)
        global_center = self.image_view.mapToGlobal(self.image_view.viewport().rect().center())
        view_pos, pix_pos = self.mouseImagePos()

        newX = int(scene_center.x() - pix_pos.x())
        newY = int(scene_center.y() - pix_pos.y())
        self.image_view.translate(newX, newY)
        self.cursor().setPos(global_center)

    def onBlur(self,value):
        self.r = floor(value)/10
        imageFilters = ImageFilters(self.image,a=self.a,b=self.b,r=self.r)
        image_blurred = imageFilters.apply()
        
        self.qimage = ImageQt(image_blurred)
        self.pixmap = self._pixmap()
        self._pixmap_item.setPixmap(self.pixmap)

    def onBrighten(self,value):
        self.a = floor(value)/10 + 1
        imageFilters = ImageFilters(self.image,a=self.a,b=self.b,r=self.r)
        image_bright = imageFilters.apply()
        
        self.qimage = ImageQt(image_bright)
        self.pixmap = self._pixmap()
        self._pixmap_item.setPixmap(self.pixmap)

    def onContrast(self,value):
        self.b = floor(value)/10 + 1
        imageFilters = ImageFilters(self.image,a=self.a,b=self.b,r=self.r)
        image_contrast = imageFilters.apply()
        
        self.qimage = ImageQt(image_contrast)
        self.pixmap = self._pixmap()
        self._pixmap_item.setPixmap(self.pixmap)

    # === Update methods ===

    def favoriteUpdate(self):
        if self.image_file in self.favorite_file_list:
            self.favorite_box.setChecked(True)
            self.favorite_box.setIcon(QIcon(__heart_solid__))
        else:
            self.favorite_box.setIcon(QIcon(__heart_clear__))
            self.favorite_box.setChecked(False)

    def imageUpdate(self):
        # Remove Marks
        for item in self.image_scene.items(): 
            if isinstance(item,Mark): self.image_scene.removeItem(item)

        # Update the pixmap
        self.image = Image.open(self.image_paths[self.idx])
        self.image_file = self.image.filename.split(os.sep)[-1]
        self.qimage = ImageQt(self.image)
        self.pixmap = self._pixmap()
        self._pixmap_item.setPixmap(self.pixmap)

        # Update image label
        self.image_label.setText(f'{self.image_file} ({self.idx+1} of {self.N})')

        #Update WCS
        self.wcs = galmark.io.parseWCS(self.image)
    
    def commentUpdate(self):
        # Update the comment in the dictionary
        comment = self.comment_box.text()
        if not comment:
            comment = 'None'

        self.data[self.image_file]['comment'] = comment
        galmark.io.save(self.data,self.username,self.date)
        galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)

    def getComment(self):
        if bool(self.data[self.image_file]['comment']):
            if (self.data[self.image_file]['comment'] == 'None'):
                self.comment_box.setText('')
            else:
                comment = self.data[self.image_file]['comment']
                self.comment_box.setText(comment)
        else:
            comment = 'None'
            self.data[self.image_file]['comment'] = comment
            self.comment_box.setText('')

    def categoryUpdate(self):
        # Initialize category and update checkboxes
        for box in self.category_boxes: box.setChecked(False)
        if not (self.data[self.image_file]['categories']):
            self.data[self.image_file]['categories'] = []
        else:
            category_list = self.data[self.image_file]['categories']
            for i in range(1,6):
                if (i in category_list):
                    self.category_boxes[i-1].setChecked(True)

    def markUpdate(self):
        # Redraws all marks in image
        for i in range(0,10):
            mark_list = self.data[self.image_file][i]['marks']
                
            for mark in mark_list: mark.draw(self.image_scene)

    def getSelectedMarks(self):
        _, pix_pos = self.mouseImagePos()
        pix_pos = pix_pos.toPointF()
        selection_filt = [ item is self.image_scene.itemAt(pix_pos, item.transform()) 
                           for item in self.image_scene.items() 
                           if isinstance(item,Mark) ]
        selected_items = [ item for item in self.image_scene.items() 
                           if isinstance(item,Mark) 
                           and (item is self.image_scene.itemAt(pix_pos, item.transform()))]
        
        for item in selected_items:
            self.image_scene.removeItem(item)
            self.data[self.image_file][item.g]['marks'].remove(item)
            galmark.io.save(self.data,self.username,self.date)
            galmark.io.save_fav(self.data,self.username,self.date,self.favorite_file_list)

    # === Transformations ===
    def zoom(self,scale:int=1):
        # Zoom in on cursor location
        view_pos, _ = self.mouseImagePos()
        transform = self.image_view.transform()
        center = self.image_view.mapToScene(view_pos)
        transform.translate(center.x(), center.y())
        transform.scale(1.2**scale, 1.2**scale)
        transform.translate(-center.x(), -center.y())
        self.image_view.setTransform(transform)

    # === Utils ===
    
    def mouseImagePos(self):
        '''
        Gets mouse positions

        Returns:
            view_pos: position of mouse in image_view
            pix_pos: position of mouse in the pixmap
        '''
        view_pos = self.image_view.mapFromGlobal(QCursor.pos())
        scene_pos = self.image_view.mapToScene(view_pos)
        pix_pos = self._pixmap_item.mapFromScene(scene_pos).toPoint()

        return view_pos, pix_pos

    