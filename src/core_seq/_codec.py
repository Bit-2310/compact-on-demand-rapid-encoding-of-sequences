"""
Internal Codec for CORE-seq

This is the engine room of the CORE-seq project. It handles the clever
tricks for squishing sequence letters into a compact binary format and
verifying that the data is not corrupted.
"""

import zlib
import numbers # We'll use this for error checking

# --- The "Letter-to-Number" Dictionary ---
# This is our dictionary for turning every possible DNA character (including
# the ambiguous ones like 'N') into a unique 4-bit number (a "nibble").
IUPAC_TO_4BIT = {
    # Using uppercase for consistency
    'A': 0x1, 'C': 0x2, 'G': 0x4, 'T': 0x8,
    'R': 0x5, 'Y': 0xA, 'S': 0x6, 'W': 0x9, # A/G, C/T, G/C, A/T
    'K': 0xC, 'M': 0x3, 'B': 0xE, 'D': 0xD, # G/T, A/C, C/G/T, A/G/T
    'H': 0xB, 'V': 0x7, 'N': 0xF, '-': 0x0
}

# And this is the reverse dictionary for turning numbers back into letters.
FOURBIT_TO_IUPAC = {v: k for k, v in IUPAC_TO_4BIT.items()}

def encode_sequence(sequence: str) -> (bytearray, int):
    """
    Takes a sequence of letters and packs them into a binary format.
    
    This works by packing two 4-bit numbers (representing two bases)
    into a single 8-bit byte.

    Args:
        sequence (str): The DNA sequence, like "GATTACA".

    Returns:
        A tuple containing:
            - bytearray: The sequence squished into binary data.
            - int: How long the original sequence was.
            
    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(sequence, str):
        raise TypeError(f"Input sequence must be a string, not {type(sequence).__name__}")

    encoded_data = bytearray()
    # Make sure we're always working with uppercase letters
    sequence = sequence.upper()
    
    # Go through the sequence, two letters at a time.
    for i in range(0, len(sequence), 2):
        # First letter becomes the "high" part of the byte.
        # If we don't recognize a character, we'll treat it as 'N'.
        high_nibble = IUPAC_TO_4BIT.get(sequence[i], 0xF) << 4

        # See if there's a second letter in this pair.
        if i + 1 < len(sequence):
            # Second letter becomes the "low" part of the byte.
            low_nibble = IUPAC_TO_4BIT.get(sequence[i+1], 0xF)
        else:
            # If the sequence has an odd number of letters, we just pad the end.
            low_nibble = 0x0

        # Combine the high and low parts into one byte.
        packed_byte = high_nibble | low_nibble
        encoded_data.append(packed_byte)

    return encoded_data, len(sequence)

def decode_sequence(encoded_data: bytearray, original_length: int) -> str:
    """
    Takes binary data and unpacks it back into a sequence of letters.

    Args:
        encoded_data (bytearray): The binary data to unpack.
        original_length (int): How long the final sequence should be.

    Returns:
        The original DNA sequence string.
        
    Raises:
        TypeError: If input data is not bytes or bytearray.
        ValueError: If original_length is not a valid number.
    """
    if not isinstance(encoded_data, (bytes, bytearray)):
        raise TypeError(f"Encoded data must be bytes or bytearray, not {type(encoded_data).__name__}")
    
    if not isinstance(original_length, numbers.Integral) or original_length < 0:
        raise ValueError(f"Original length must be a non-negative integer, not {original_length}")
        
    decoded_chars = []
    
    for byte in encoded_data:
        # Pull out the first letter (the "high" part) by shifting bits right.
        high_nibble = byte >> 4
        decoded_chars.append(FOURBIT_TO_IUPAC.get(high_nibble, 'N'))
        
        # Stop if we've rebuilt the original sequence.
        if len(decoded_chars) == original_length:
            break
            
        # Pull out the second letter (the "low" part) by masking bits.
        low_nibble = byte & 0x0F
        decoded_chars.append(FOURBIT_TO_IUPAC.get(low_nibble, 'N'))

        # Stop if we've rebuilt the original sequence.
        if len(decoded_chars) == original_length:
            break

    return "".join(decoded_chars)

def calculate_checksum(data: bytes) -> int:
    """
    Calculates a "digital fingerprint" (CRC32 checksum) for the data.
    This helps us check if the file has been corrupted.

    Args:
        data (bytes): The binary data.

    Returns:
        The 32-bit checksum, as an integer.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"Checksum input must be bytes or bytearray, not {type(data).__name__}")
    return zlib.crc32(data)

def verify_checksum(data: bytes, expected_checksum: int) -> bool:
    """
    Checks if the data's fingerprint matches the one we have on record.

    Args:
        data (bytes): The binary data.
        expected_checksum (int): The original fingerprint we're checking against.

    Returns:
        True if the data is intact, False if it's been changed or corrupted.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"Checksum input must be bytes or bytearray, not {type(data).__name__}")
    return calculate_checksum(data) == expected_checksum

