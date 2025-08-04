import PyPDF2
import openai


def classify(pdf_path: str) -> str:
    """
    Reads a PDF from the given path and returns its full text as a single string.
    """
    reader = PyPDF2.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    client = GPTClient()
    print(text)
    
    messages = client.system_messages + [
        {"role": "user", "content": text},
        {"role": "user", "content": "Please return the denial reason in the given format"}
    ]

    # 3) Call the model and return its reply
    return client.chat(messages)

class GPTClient:
    """
    Simple OpenAI GPT client wrapper.
    """
    def __init__(self, model: str = "gpt-4o-mini"):
        
        self.model = model
        self.system_messages = [
            {"role":"system","content":"You are an expert in insurance denials and reading and deducing why claims were denied."},
            {"role":"system","content":"I am going to give you a document that is a claim denial. I want you to read the document and understand the claim."},
            {"role":"system","content":"First deduce if the denial reason is either Structural or Editable. Structural means that the claim was denied because the patient simply does not have coverage, the plan is simply not covered or reasons we cannot make changes to the claim for, they are simply denied and we cannot fix it is when I want Sturctural."},
            {"role":"system","content":"If the denial reason is Editable, then I want you to read the document and understand the claim. I want you to understand the claim and then figure out if is a claim that is denied for missing xrays or images or denied for other reasons."},
            {"role":"system","content":"If Structural, then I want you to return string Struct. If Editable and xray missing return xray or return editOther if the denial is editable but for other reasons"},
        ]

    def chat(self, messages: list) -> str:
       
        response = openai.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content or ""


def main():
    # Update this path to point to your PDF file
    print("1")

    pdf_path = "/Users/nishanthkankipati/Documents/test1.pdf"
    print("2")
    classification = classify(pdf_path)
    print("3")
    print("Denial classification:", classification)

if __name__ == "__main__":
    main()

