from flask import Flask, render_template, request, send_file, jsonify
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer, RoundedModuleDrawer, SquareModuleDrawer, GappedSquareModuleDrawer, VerticalBarsDrawer, HorizontalBarsDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from io import BytesIO
import base64
from PIL import Image, ImageDraw
import os
import math

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Map for module drawer styles
MODULE_DRAWERS = {
    'square': SquareModuleDrawer(),
    'circle': CircleModuleDrawer(),
    'rounded': RoundedModuleDrawer(),
    'gapped': GappedSquareModuleDrawer(),
    'vertical_bars': VerticalBarsDrawer(),
    'horizontal_bars': HorizontalBarsDrawer()
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_gradient_image(width, height, color1, color2, gradient_type):
    """Create a gradient image manually since built-in gradients aren't available"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    if gradient_type == 'linear':
        # Linear horizontal gradient
        for x in range(width):
            ratio = x / width
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    elif gradient_type == 'radial':
        # Radial gradient from center
        center_x, center_y = width // 2, height // 2
        max_distance = math.sqrt(center_x**2 + center_y**2)
        
        for y in range(height):
            for x in range(width):
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                ratio = min(1.0, distance / max_distance)
                r = int(r1 * (1 - ratio) + r2 * ratio)
                g = int(g1 * (1 - ratio) + g2 * ratio)
                b = int(b1 * (1 - ratio) + b2 * ratio)
                draw.point((x, y), fill=(r, g, b))
    
    elif gradient_type == 'diagonal':
        # Diagonal gradient
        for y in range(height):
            for x in range(width):
                ratio = (x + y) / (width + height)
                r = int(r1 * (1 - ratio) + r2 * ratio)
                g = int(g1 * (1 - ratio) + g2 * ratio)
                b = int(b1 * (1 - ratio) + b2 * ratio)
                draw.point((x, y), fill=(r, g, b))
    
    return img

def apply_gradient_to_qr(qr_img, color1, color2, gradient_type):
    """Apply gradient colors to QR code modules"""
    # Convert to RGB mode if needed
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    width, height = qr_img.size
    
    # Create gradient based on QR code structure
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    # Create a pixel map
    pixels = qr_img.load()
    
    for y in range(height):
        for x in range(width):
            current_color = pixels[x, y]
            
            # Only recolor non-background pixels (assuming black/dark is QR modules)
            # Check if pixel is not white/background
            if current_color != (255, 255, 255):
                if gradient_type == 'linear':
                    # Linear horizontal gradient
                    ratio = x / width
                    r = int(r1 * (1 - ratio) + r2 * ratio)
                    g = int(g1 * (1 - ratio) + g2 * ratio)
                    b = int(b1 * (1 - ratio) + b2 * ratio)
                    pixels[x, y] = (r, g, b)
                
                elif gradient_type == 'radial':
                    # Radial gradient from center
                    center_x, center_y = width // 2, height // 2
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    max_distance = math.sqrt(center_x**2 + center_y**2)
                    ratio = min(1.0, distance / max_distance)
                    r = int(r1 * (1 - ratio) + r2 * ratio)
                    g = int(g1 * (1 - ratio) + g2 * ratio)
                    b = int(b1 * (1 - ratio) + b2 * ratio)
                    pixels[x, y] = (r, g, b)
                
                elif gradient_type == 'diagonal':
                    # Diagonal gradient
                    ratio = (x + y) / (width + height)
                    r = int(r1 * (1 - ratio) + r2 * ratio)
                    g = int(g1 * (1 - ratio) + g2 * ratio)
                    b = int(b1 * (1 - ratio) + b2 * ratio)
                    pixels[x, y] = (r, g, b)
    
    return qr_img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    # Get parameters from the form
    data = request.form.get('data', '')
    version = request.form.get('version', None, type=int)
    box_size = request.form.get('box_size', 10, type=int)
    border = request.form.get('border', 4, type=int)
    error_correction = request.form.get('error_correction', 'M')
    module_style = request.form.get('module_style', 'circle')
    embed_image = request.form.get('embed_image') == 'on'
    
    # Color parameters
    color_type = request.form.get('color_type', 'solid')
    front_color = request.form.get('front_color', '#000000')
    back_color = request.form.get('back_color', '#FFFFFF')
    gradient_color1 = request.form.get('gradient_color1', '#FF0000')
    gradient_color2 = request.form.get('gradient_color2', '#0000FF')
    gradient_type = request.form.get('gradient_type', 'linear')
    
    if not data:
        return jsonify({'error': 'Please enter some data'}), 400
    
    # Map error correction levels
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    selected_correction = error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M)
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=version,
        error_correction=selected_correction,
        box_size=box_size,
        border=border,
    )
    
    # Add data
    qr.add_data(data)
    qr.make(fit=True)
    
    # Get the selected module drawer
    module_drawer = MODULE_DRAWERS.get(module_style, CircleModuleDrawer())
    
    # Create base QR code (black and white first)
    if color_type == 'solid':
        # Use SolidFillColorMask for solid colors
        color_mask = SolidFillColorMask(
            front_color=hex_to_rgb(front_color),
            back_color=hex_to_rgb(back_color)
        )
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask
        )
    else:
        # For gradients, create B&W QR first, then apply gradient
        color_mask = SolidFillColorMask(
            front_color=(0, 0, 0),
            back_color=(255, 255, 255)
        )
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask
        )
        # Apply gradient to the QR modules
        qr_img = apply_gradient_to_qr(qr_img, gradient_color1, gradient_color2, gradient_type)
        
        # Apply background color if not white
        if back_color != '#FFFFFF':
            # Create background with color
            background = Image.new('RGB', qr_img.size, hex_to_rgb(back_color))
            # Composite QR onto background
            qr_img = Image.composite(qr_img, background, qr_img)
    
    # Handle embedded image if requested
    temp_img_path = None
    if embed_image and 'image_file' in request.files:
        image_file = request.files['image_file']
        if image_file and image_file.filename != '':
            try:
                temp_img_path = 'temp_logo.png'
                image_file.save(temp_img_path)
                
                # Open and resize logo
                logo = Image.open(temp_img_path)
                qr_width, qr_height = qr_img.size
                logo_size = int(min(qr_width, qr_height) * 0.25)
                logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Calculate position
                pos = ((qr_width - logo.width) // 2, (qr_height - logo.height) // 2)
                
                # Convert to RGBA if needed
                if qr_img.mode != 'RGBA':
                    qr_img = qr_img.convert('RGBA')
                if logo.mode != 'RGBA':
                    logo = logo.convert('RGBA')
                
                # Paste logo
                qr_img.paste(logo, pos, logo)
                
            except Exception as e:
                print(f"Error embedding image: {e}")
            finally:
                if temp_img_path and os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
    
    # Convert to base64 for inline display
    buffered = BytesIO()
    # Convert back to RGB for PNG
    if qr_img.mode == 'RGBA':
        qr_img = qr_img.convert('RGB')
    qr_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Get style names for display
    style_names = {
        'square': 'Square',
        'circle': 'Circle',
        'rounded': 'Rounded Corners',
        'gapped': 'Gapped Squares',
        'vertical_bars': 'Vertical Bars',
        'horizontal_bars': 'Horizontal Bars'
    }
    
    color_names = {
        'solid': 'Solid Color',
        'linear_gradient': 'Linear Gradient',
        'radial_gradient': 'Radial Gradient',
        'diagonal_gradient': 'Diagonal Gradient'
    }
    
    return f'''
        <div class="qr-result" id="qr-result">
            <h3>✨ Your Custom QR Code</h3>
            <div class="qr-container">
                <img src="data:image/png;base64,{img_base64}" alt="QR Code" id="generated-qr">
            </div>
            <div class="qr-details">
                <p><strong>📝 Data:</strong> {data[:50]}{'...' if len(data) > 50 else ''}</p>
                <p><strong>🎨 Style:</strong> {style_names.get(module_style, 'Circle')}</p>
                <p><strong>🎨 Color:</strong> {color_names.get(color_type, 'Solid')}</p>
                <p><strong>📊 Version:</strong> {version if version else 'Auto'} | <strong>Box Size:</strong> {box_size}px</p>
            </div>
            <button onclick="downloadQR()" class="download-btn">💾 Download QR Code</button>
        </div>
    '''

@app.route('/download-qr', methods=['POST'])
def download_qr():
    data = request.form.get('data', '')
    version = request.form.get('version', None, type=int)
    box_size = request.form.get('box_size', 10, type=int)
    border = request.form.get('border', 4, type=int)
    error_correction = request.form.get('error_correction', 'M')
    module_style = request.form.get('module_style', 'circle')
    embed_image = request.form.get('embed_image') == 'on'
    
    # Color parameters
    color_type = request.form.get('color_type', 'solid')
    front_color = request.form.get('front_color', '#000000')
    back_color = request.form.get('back_color', '#FFFFFF')
    gradient_color1 = request.form.get('gradient_color1', '#FF0000')
    gradient_color2 = request.form.get('gradient_color2', '#0000FF')
    gradient_type = request.form.get('gradient_type', 'linear')
    
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    selected_correction = error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M)
    
    qr = qrcode.QRCode(
        version=version,
        error_correction=selected_correction,
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    module_drawer = MODULE_DRAWERS.get(module_style, CircleModuleDrawer())
    
    # Create QR code
    if color_type == 'solid':
        color_mask = SolidFillColorMask(
            front_color=hex_to_rgb(front_color),
            back_color=hex_to_rgb(back_color)
        )
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask
        )
    else:
        # Create B&W QR first
        color_mask = SolidFillColorMask(
            front_color=(0, 0, 0),
            back_color=(255, 255, 255)
        )
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask
        )
        # Apply gradient
        qr_img = apply_gradient_to_qr(qr_img, gradient_color1, gradient_color2, gradient_type)
        
        # Apply background color if needed
        if back_color != '#FFFFFF':
            background = Image.new('RGB', qr_img.size, hex_to_rgb(back_color))
            qr_img = Image.composite(qr_img, background, qr_img)
    
    # Handle embedded image
    temp_img_path = None
    if embed_image and 'image_file' in request.files:
        image_file = request.files['image_file']
        if image_file and image_file.filename != '':
            try:
                temp_img_path = 'temp_download_logo.png'
                image_file.save(temp_img_path)
                
                logo = Image.open(temp_img_path)
                qr_width, qr_height = qr_img.size
                logo_size = int(min(qr_width, qr_height) * 0.25)
                logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                pos = ((qr_width - logo.width) // 2, (qr_height - logo.height) // 2)
                
                if qr_img.mode != 'RGBA':
                    qr_img = qr_img.convert('RGBA')
                if logo.mode != 'RGBA':
                    logo = logo.convert('RGBA')
                
                qr_img.paste(logo, pos, logo)
                
            except Exception as e:
                print(f"Error embedding image: {e}")
            finally:
                if temp_img_path and os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
    
    buffered = BytesIO()
    if qr_img.mode == 'RGBA':
        qr_img = qr_img.convert('RGB')
    qr_img.save(buffered, format="PNG")
    buffered.seek(0)
    
    return send_file(buffered, mimetype='image/png', as_attachment=True, 
                    download_name='custom_qrcode.png')

if __name__ == '__main__':
    app.run(debug=True)