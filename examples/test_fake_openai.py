from openai import OpenAI

client = OpenAI(api_key="ef19e6b7-d8e3-4a76-91c0-be50029dd332", base_url="http://localhost:30081/v1")

response = client.chat.completions.create(
    model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Which function implements NSST creation?"}]
)

print(response)
