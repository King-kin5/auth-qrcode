def generate_qr_code(data, size=10):
    """
    Generate QR code matrix without using external libraries
    
    Args:
        data (str): Content to encode
        size (int): Size multiplier for pixel density
    
    Returns:
        list: 2D matrix representing QR code
    """
    # Implement Reed-Solomon error correction
    def reed_solomon_encode(data):
        # Basic error correction implementation
        prime = 285  # QR code's Galois Field prime
        generator_poly = [1]
        
        for i in range(8):  # 8-bit error correction
            new_poly = [1, pow(2, i, prime)]
            generator_poly = multiply_polynomials(generator_poly, new_poly, prime)
        
        return generator_poly

    # Polynomial multiplication for error correction
    def multiply_polynomials(a, b, prime):
        result = [0] * (len(a) + len(b) - 1)
        for i in range(len(a)):
            for j in range(len(b)):
                result[i+j] ^= (a[i] * b[j]) % prime
        return result

    # Binary data encoding
    def encode_data(input_data):
        binary_data = ''.join(format(ord(c), '08b') for c in input_data)
        return binary_data

    # Create base matrix with positioning patterns
    def create_base_matrix():
        matrix = [[0 for _ in range(21)] for _ in range(21)]
        
        # Finder patterns
        def draw_finder_pattern(x, y):
            for i in range(7):
                for j in range(7):
                    if (i in [0, 6] or j in [0, 6]) or (1 <= i <= 5 and 1 <= j <= 5):
                        matrix[y+i][x+j] = 1
                    if 2 <= i <= 4 and 2 <= j <= 4:
                        matrix[y+i][x+j] = 0

        draw_finder_pattern(0, 0)  # Top-left
        draw_finder_pattern(14, 0)  # Top-right
        draw_finder_pattern(0, 14)  # Bottom-left

        return matrix

    # Encode and place data
    binary_data = encode_data(data)
    error_correction = reed_solomon_encode(binary_data)
    
    matrix = create_base_matrix()
    
    # Placeholder for actual data placement logic
    for i, bit in enumerate(binary_data):
        row = i // 21
        col = i % 21
        if matrix[row][col] == 0:
            matrix[row][col] = int(bit)

    return matrix