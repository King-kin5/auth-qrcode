#qrservice

from backend.util import generate_qr_code

import qrcode
import io
import base64

class QRService:
    def create_qr(self, content: str, size: int = 10):
        """
        Service layer for QR code generation with enhanced robustness
        
        Args:
            content (str): Content to encode in QR code
            size (int): Size multiplier for QR code
        
        Returns:
            str: SVG representation of the QR code
        """
        # Validate input
        if not content:
            raise ValueError("Content cannot be empty")
        
        # Limit content length to prevent excessive QR code size
        content = content[:500]  # Adjust as needed
        
        # Create QR code with comprehensive configuration
        qr = qrcode.QRCode(
            version=None,  # Auto-determine version
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction
            box_size=size,  # Pixel size of each box
            border=4,  # White space around the QR code
        )
        
        # Add data and generate
        qr.add_data(content)
        qr.make(fit=True)
        
        # Convert to SVG with detailed rendering
        return self.convert_to_svg(qr, size)
    
    def convert_to_svg(self, qr, pixel_size=10):
        """
        Convert QR code to a comprehensive SVG representation
        
        Args:
            qr (qrcode.QRCode): QR code instance
            pixel_size (int): Size of each QR code module
        
        Returns:
            str: Detailed SVG string
        """
        # Get the QR code matrix
        matrix = qr.get_matrix()
        
        # Determine dimensions with padding
        width = len(matrix)
        svg_width = width * pixel_size
        
        # Start SVG generation with comprehensive attributes
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width}" '
            f'height="{svg_width}" '
            f'viewBox="0 0 {svg_width} {svg_width}" '
            f'shape-rendering="crispEdges">'
        ]
        
        # White background with slight transparency
        svg.append('<rect width="100%" height="100%" fill="white" fill-opacity="0.9"/>')
        
        # Render QR code modules with optimized rendering
        for y, row in enumerate(matrix):
            for x, cell in enumerate(row):
                if cell:
                    svg.append(
                        f'<rect x="{x*pixel_size}" '
                        f'y="{y*pixel_size}" '
                        f'width="{pixel_size}" '
                        f'height="{pixel_size}" '
                        f'fill="black"/>'
                    )
        
        svg.append('</svg>')
        return ''.join(svg)