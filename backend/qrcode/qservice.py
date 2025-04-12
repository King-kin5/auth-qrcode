import qrcode

class QRService:
    def create_qr(self, content: str, size: int = 10):
        """
        Generate a QR code for a given URL (or content).
        The content is now expected to be a short URL.
        """
        if not content:
            raise ValueError("Content cannot be empty")
        
        # If your content is just a URL, you likely don't need to perform any
        # truncation as URLs will be much shorter than 20,000 characters.
        
        qr = qrcode.QRCode(
            version=None,  # Auto-detect version
            error_correction=qrcode.constants.ERROR_CORRECT_Q,  # High error correction
            box_size=size,
            border=4,
        )
        
        qr.add_data(content)
        qr.make(fit=True)
        
        return self.convert_to_svg(qr, size)
    
    def convert_to_svg(self, qr, pixel_size=10):
        matrix = qr.get_matrix()
        width = len(matrix)
        svg_width = width * pixel_size
        
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width}" height="{svg_width}" '
            f'viewBox="0 0 {svg_width} {svg_width}" '
            f'shape-rendering="crispEdges">'
        ]
        
        svg.append('<rect width="100%" height="100%" fill="white" fill-opacity="0.9"/>')
        
        for y, row in enumerate(matrix):
            for x, cell in enumerate(row):
                if cell:
                    svg.append(
                        f'<rect x="{x*pixel_size}" y="{y*pixel_size}" '
                        f'width="{pixel_size}" height="{pixel_size}" fill="black"/>'
                    )
        
        svg.append('</svg>')
        return ''.join(svg)
