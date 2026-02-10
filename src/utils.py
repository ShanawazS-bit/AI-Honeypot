import re

def text_to_digits(text: str) -> str:


        # Simple word replacement

    """
    Converts number words to digits in a string.
    Example: "one two three" -> "123"
    Example: "account number five six seven" -> "account number 567"
    """



    
    if not text:
        return text
        
    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'oh': '0'
    }
    
    words = text.lower().split()
    new_words = []
    
    for word in words:
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word in word_to_digit:
            new_words.append(word_to_digit[clean_word])
        else:
            new_words.append(word)
            
    return ' '.join(new_words)
