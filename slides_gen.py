import openai
import toml
import re
import json

def load_api_key():
    secrets = toml.load("secrets.toml")
    return secrets.get("openai_key", "")

def md_split(text):
    section_pattern = r'(^#+\s.*)|(^\*\*.*\*\*$)|(^[A-Z][A-Z\s]+\n)'
    sections = re.split(section_pattern, text, flags=re.MULTILINE)
    slides = []
    current_slide = ""
    
    for part in sections:
        if part and re.match(section_pattern, part):
            if current_slide:
                slides.append(current_slide.strip())
            current_slide = part
        elif part:
            current_slide += "\n" + part
    
    if current_slide:
        slides.append(current_slide.strip())
    
    print(f"Initial split into {len(slides)} sections.")
    return slides

def count_words(text):
    """Returns the word count of the given text."""
    return len(text.split())

def count_paragraphs(text):
    """Returns the number of paragraphs in the given text."""
    return len([p for p in text.split("\n") if p.strip()])  # Count non-empty lines

def get_merge_decision(client, slides):
    """Determines which two adjacent sections to merge based on word and paragraph count."""
    
    # Calculate word and paragraph count for each slide
    slide_metadata = [
        {
            "index": i,
            "text": slide,
            "words": count_words(slide),
            "paragraphs": count_paragraphs(slide),
        }
        for i, slide in enumerate(slides)
    ]
    
    # Format slides for LLM with word & paragraph counts
    slides_formatted = [
        f"{s['index']}: ({s['words']} words, {s['paragraphs']} paragraphs) {s['text']}"
        for s in slide_metadata
    ]

    prompt = f"""
    ## **Task: Choose which sections to merge**
    You are given a markdown document that has been split into sections, represented as a JSON list. 
    Your task is to **identify two adjacent sections** that make the most sense to merge based on their conveyed ideas while keeping section sizes balanced.

    ## **Merging Criteria**
    - The starting section index is zero.
    - Aim to merge the two **smallest adjacent sections** based on **word count and paragraph count**.
    - Take the text content into account when deciding what to merge, the merged sections should be more strongly related in their conveyed ideas than the alternatives.
    - If a section contains a single sentence or title, prioritize it for merging onto the section that's right after it before any theme-based merging.
    
    
    ## **Current Sections (with Word & Paragraph Count)**
    ```json
    {json.dumps(slides_formatted)}
    ```

    ## **Expected Output Format**
    Return JSON like:
    ```json
    [0, 1]
    ```
    ### **You must only return the JSON and nothing else. No explanations.**
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert in document structuring."},
                  {"role": "user", "content": prompt}]
    )
    
    json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
    return json.loads(json_response)


def get_split_decision(client, slides):
    """Decides which slide should be split when we have too few."""
    prompt = f"""You are optimizing a slide presentation.
    There are currently {len(slides)} slides, and we need more.
    
    Return a single section number that should be split based on size and content.
    Choose a slide that contains distinct ideas that can be separated.

    Slides:
    {json.dumps([f'{i}: {slide[:200]}' for i, slide in enumerate(slides)])}

    Return JSON like:
    ```json
    [2]
    ```
    ### You must only return the json and nothing else, no comments, no supplemental text.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert in document structuring."},
                  {"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
    return json.loads(json_response)

def ai_adjust(slides, num_slides):
    api_key = load_api_key()
    client = openai.OpenAI(api_key=api_key)
    
    while len(slides) != num_slides:
        if len(slides) > num_slides:
            decision = get_merge_decision(client, slides)
            merge_index1, merge_index2 = sorted(decision)  # Ensure lower index is first
            print(f"Merging slides {merge_index1} and {merge_index2}")  # Debugging line
            slides[merge_index1] = slides[merge_index1] + "\n\n" + slides.pop(merge_index2)

        elif len(slides) < num_slides:
            decision = get_split_decision(client, slides)
            split_index = decision[0]
            largest_slide = slides.pop(split_index)

            prompt = f"""Split the following markdown text into 2 parts, ensuring each part conveys distinct ideas but retains original content.
            
            TEXT:
            {largest_slide}
            
            Return a JSON array of strings:
            ```json
            ["Part 1...", "Part 2..."]
            ```
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are an expert in document structuring."},
                          {"role": "user", "content": prompt}]
            )

            json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
            sections = json.loads(json_response)
            slides.insert(split_index, sections[1].strip())
            slides.insert(split_index, sections[0].strip())

    return slides

# Main function to read Markdown and generate slides
def main():
    input_file = "input2.md"
    num_slides = 2  # Target number of slides

    with open(input_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    slides = md_split(md_content)
    output = ""
    for i, slide in enumerate(slides, 1):
        output+= f"\nSlide {i}:\n{slide}"
    with open("output_unrefined.txt", "w", encoding="utf-8") as f:
        f.write(f"{output}")
    
    slides = ai_adjust(slides, num_slides)

    output = ""
    for i, slide in enumerate(slides, 1):
        output+= f"\nSlide {i}:\n{slide}"
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(f"{output}")

if __name__ == "__main__":
    main()
