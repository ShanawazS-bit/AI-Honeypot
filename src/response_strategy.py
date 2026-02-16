import random

class ResponseStrategy:
    """
    Determines the best response based on the detected Scam Type and Risk profile.
    Uses a 'Curious/Confused' persona to elicit actionable intelligence.
    """
    
    @staticmethod
    def generate_response(scam_type: str, text_input: str) -> str:
        lower_input = text_input.lower()
        
        # 1. Bank Fraud Probing
        if scam_type == "bank_fraud":
            if "otp" in lower_input:
                return random.choice([
                    "OTP? I didn't get any SMS. Can you send it again? Which number it comes from?",
                    "My phone is old... where do I see the OTP? Is it in the bank app?"
                ])
            if "block" in lower_input or "suspend" in lower_input:
                return random.choice([
                    "Blocked? Oh no! I have my pension in SBI. Which branch are you calling from?",
                    "Can I come to the branch personally? I don't know how to do online. What is your address?"
                ])
            return "My bank details? I am scared... can you tell me your Employee ID first so I can note it down?"

        # 2. UPI Fraud Probing
        if scam_type == "upi_fraud":
            if "cashback" in lower_input or "refund" in lower_input:
                return random.choice([
                    "Cashback? 5000 rupees? Wow! Do I need to open Google Pay or PhonePe?",
                    "I received a message... but it says 'Pay'. Use 'Receive' na? How to do it?"
                ])
            if "pin" in lower_input or "scan" in lower_input:
                return "Enter PIN? But I am receiving money... why PIN? My layman neighbor said PIN is for giving money."
            return "I have GPay. What is your VPA ID? I can try to send 1 rupee to check."

        # 3. Phishing Probing
        if scam_type == "phishing":
            return random.choice([
                "The link is not opening... it says 'Safety Warning'. Do you have a secure https website?",
                "I clicked it but screen is blank. Can you spell the website name? I will type it in Chrome.",
                "Is this the official site? My son said always check for 'lock' icon. I don't see it."
            ])
            
        # 4. Digital Arrest / Police Scam (High Risk)
        if "police" in lower_input or "arrest" in lower_input:
            return random.choice([
                "Arrest? I am 72 years old! I never did anything. Which Police Station is this?",
                "Please don't arrest... I will cooperate. What is your Badge Number? I want to tell my lawyer.",
                "Can I call the SP? I know the local inspector. What is your name sir?"
            ])

        # 5. Default Fallback (General Confusion)
        return random.choice([
            "Hello? Your voice is breaking... who is this exactly?",
            "I don't understand these technical things. Can you explain slowly?",
            "My grandson usually handles this... can you wait for him? Or tell me what to write down."
        ])
