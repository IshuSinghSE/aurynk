#!/usr/bin/env python3
"""QR code widget for displaying QR codes in the UI."""

import io
import gi

from aurynk.utils.logger import get_logger

logger = get_logger("QRWidget")

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GdkPixbuf

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers.pil import CircleModuleDrawer
except ImportError:
    qrcode = None


def create_qr_widget(data: str, size: int = 200) -> Gtk.Box:
    """
    Create a GTK widget containing a QR code.
    
    Args:
        data: The data to encode in the QR code
        size: The size of the QR code in pixels
        
    Returns:
        A Gtk.Box containing the QR code image
    """
    qr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    qr_box.set_valign(Gtk.Align.CENTER)
    qr_box.set_halign(Gtk.Align.CENTER)

    if qrcode is None:
        # Fallback if qrcode library is not available
        error_label = Gtk.Label(label="QR code library not available")
        error_label.add_css_class("dim-label")
        qr_box.append(error_label)
        return qr_box

    try:
        # Generate QR code
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(data)

        qr_image = qr.make_image(image_factory=StyledPilImage, module_drawer=CircleModuleDrawer())

        # Convert to PNG bytes
        buf = io.BytesIO()
        qr_image.save(buf, format='PNG')
        buf.seek(0)

        # Load into GTK
        pixbuf_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        pixbuf_loader.write(buf.getvalue())
        pixbuf_loader.close()
        pixbuf = pixbuf_loader.get_pixbuf()

        # Create image widget
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)

        if hasattr(image, 'set_pixel_size'):
            image.set_pixel_size(size)
            
        # Wrap in a frame for rounded corners
        frame = Gtk.Frame()
        frame.set_child(image)
        frame.add_css_class("qr-image")
        frame.set_valign(Gtk.Align.CENTER)
        frame.set_halign(Gtk.Align.CENTER)
        qr_box.append(frame)

    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        error_label = Gtk.Label(label=f"Error: {e}")
        error_label.add_css_class("dim-label")
        qr_box.append(error_label)

    return qr_box
