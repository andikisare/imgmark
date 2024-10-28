from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem 
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt
import imgmarker.mark
from imgmarker import __dirname__, SUPPORTED_EXTS
import imgmarker.io
import os
from math import floor
import PIL.Image, PIL.ImageFile
from PIL.ImageFilter import GaussianBlur
from PIL.ImageEnhance import Contrast, Brightness
from astropy.wcs import WCS
from math import nan
from astropy.io import fits
import numpy as np
import typing

def open(path:str) -> Image | None:
    """
    Opens the given image file.

    Parameters
    ----------
    path: str 
        Path to the image.
    
    Returns
    ----------
    img: `imgmarker.image.Image`
        Returns the image as a Image object.
    """

    Image.MAX_IMAGE_PIXELS = None # change this if we want to limit the image size
    ext = path.split('.')[-1]

    if ext in SUPPORTED_EXTS:
        img = Image()

        if (ext == 'fits') or (ext == 'fit'):
            file = fits.open(path)
            img_array = np.flipud(file[0].data).byteswap()
            img_pil = PIL.Image.fromarray(img_array, mode='F').convert('RGB')
            img_pil.format = 'FITS'
            img_pil.filename = path

        else: img_pil = PIL.Image.open(path)

        # Setup  __dict__
        img.__dict__ =  img_pil.__dict__
        try: img.n_frames = img_pil.n_frames
        except: img.n_frames = 1
        img.wcs = imgmarker.io.parse_wcs(img_pil)
        img.image_file = img_pil
        img.name = path.split(os.sep)[-1] 

        img.r = 0.0
        img.a = 1.0
        img.b = 1.0

        img.comment = 'None'
        img.categories = []
        img.marks = []
        img.ext_marks = []
        img.seen = False
        img.frame = 0

        # Get bytes from image (I dont think this does anything)
        img.frombytes(img_pil.tobytes())

        super(QGraphicsPixmapItem,img).__init__(QPixmap())

        return img
    
class Image(PIL.Image.Image,QGraphicsPixmapItem):
    """Image class based on the Python Pillow Image class and merged with the PyQt6 QGraphicsPixmapItem."""
    
    def __init__(self):
        """Initialize from parents."""
        
        super().__init__()

        self.image_file:PIL.ImageFile.ImageFile
        self.wcs:WCS
        self.n_frames:int
        self.name:str
        self.r:float
        self.a:float
        self.b:float
        self.comment:str
        self.categories:list[str]
        self.marks:list[imgmarker.mark.Mark]
        self.ext_marks:list[imgmarker.mark.Mark]
        self.seen:bool
        self.frame:int

    def _new(self, im) -> Image:
        """Internal PIL.Image.Image method for making a copy of the image."""
        new = Image()
        new.im = im
        new._mode = im.mode
        new._size = im.size
        if im.mode in ("P", "PA"):
            if self.palette:
                new.palette = self.palette.copy()
            else:
                from PIL import ImagePalette

                new.palette = ImagePalette.ImagePalette()
        new.info = self.info.copy()
        return new
    
    def clear(self): self.setPixmap(QPixmap())
    
    def tell(self): return self.image_file.tell()

    def seek(self,frame:int=0):
        """Parses through the frames in a TIFF image."""

        frame = floor(frame)
        
        if frame > self.n_frames - 1: frame = 0
        elif frame < 0: frame = self.n_frames - 1

        self.image_file.seek(frame)

        self.__dict__ = self.image_file.__dict__
        self.frombytes(self.image_file.tobytes())
        self.setPixmap(self.pixmap())
    
    def pixmap(self) -> QPixmap:
        """Creates a QPixmap item with a pillows on each side to allow for fully zooming out."""

        qimage = self.toqimage()
        pixmap_base = QPixmap.fromImage(qimage)

        w, h = self.width, self.height
        _x, _y = int(w*4), int(h*4)

        pixmap = QPixmap(w*9,h*9)
        pixmap.fill(Qt.GlobalColor.black)

        painter = QPainter(pixmap)
        painter.drawPixmap(_x, _y, pixmap_base)
        painter.end()

        return pixmap
    
    def adjust(self) -> Image:
        """Defines each image modification parameter and returns a composite filter."""
        def _blur(img:Image):
            return img.filter(GaussianBlur(self.r))
        def _brighten(img:Image):
            return Brightness(img).enhance(self.a)
        def _contrast(img:Image):
            return Contrast(img).enhance(self.b)
        
        img_filt = _contrast(_brighten(_blur(self)))
        gimg_filt = self.copy()
        gimg_filt.frombytes(img_filt.tobytes())

        return gimg_filt
    
    def blur(self,value):
        """Applies the blur value to a filter and displays it."""

        self.r = floor(value)/10
        pixmap_blurred = self.adjust().pixmap()
        self.setPixmap(pixmap_blurred)

    def brighten(self,value):
        """Applies the brighten value to a filter and displays it."""

        self.a = floor(value)/10 + 1
        pixmap_bright = self.adjust().pixmap()
        self.setPixmap(pixmap_bright)

    def contrast(self,value):
        """Applies the contrast value to a filter and displays it."""

        self.b = floor(value)/10 + 1
        pixmap_contrast = self.adjust().pixmap()
        self.setPixmap(pixmap_contrast)

    def wcs_center(self) -> list:
        try: return self.wcs.all_pix2world([[self.width/2, self.height/2]], 0)[0]
        except: return nan, nan
            
class ImageScene(QGraphicsScene):
    """A class for storing and manipulating the information/image that is currently displayed."""
    def __init__(self,image:Image):
        super().__init__()
        self.image = image

        self.setBackgroundBrush(Qt.GlobalColor.black)
        self.addItem(self.image)

    def update(self,image:Image):
        """Updates the current image with a new image."""
        # Remove items
        for item in self.items(): self.removeItem(item)

        # Update the pixmap
        self.image = image
        self.addItem(self.image)
        self.setSceneRect(0,0,9*self.image.width,9*self.image.height)

    @typing.overload
    def mark(self,x:float,y:float,shape='ellipse',text:int|str=0) -> imgmarker.mark.Mark: ...
    @typing.overload
    def mark(self,ra:float=None,dec:float=None,shape='ellipse',text:int|str=0) -> imgmarker.mark.Mark: ...
    @typing.overload
    def mark(self,mark:imgmarker.mark.Mark) -> imgmarker.mark.Mark: ... 

    def mark(self,*args,**kwargs) -> imgmarker.mark.Mark:
        """Creates a mark object and adds it to the image scene and returns the mark."""

        if len(args) == 1: mark = args[0]
        else: mark = imgmarker.mark.Mark(*args,image=self.image,**kwargs)
        self.addItem(mark.label)
        self.addItem(mark)
        return mark
    
    def rmmark(self,mark:imgmarker.mark.Mark) -> None:
        """Removes the specified mark from the image scene."""

        self.removeItem(mark)
        self.removeItem(mark.label)
