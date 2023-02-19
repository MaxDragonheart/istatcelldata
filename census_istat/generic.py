import chardet


def check_encoding(data: str):
    """Check file encoding

    Args:
        data: str

    Returns:
        str
    """
    # Look at the first ten thousand bytes to guess the character encoding
    with open(data, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))

        if result['encoding'] == 'ascii':
            result['encoding'] = 'latin1'

    return result['encoding']
