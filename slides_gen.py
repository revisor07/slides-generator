#!/usr/bin/env python3
"""
Python program to convert a Markdown file into a list of slides.
"""
import openai
import toml
import re
import json


def load_api_key():
    """Load the OpenAI API key from the secrets.toml file."""
    secrets = toml.load("secrets.toml")
    return secrets.get("openai_key", "")


def headings_split(text):
    """
    Splits a Markdown document into sections based on headings or significant formatting.

    Sections are identified using:
    - Markdown headers (#, ##, etc.)
    - Bolded text (e.g., **Title**)
    - Fully capitalized lines

    Args:
        text (str): The input Markdown text.

    Returns:
        list: A list of extracted sections as strings.
    """
    section_pattern = r'(^#+\s.*)|(^\*\*.*\*\*$)' 
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
    """
    Count the number of words in a given text.

    Args:
        text (str): The input text.

    Returns:
        int: Word count.
    """
    return len(text.split())


def count_paragraphs(text):
    """
    Count the number of paragraphs (non-empty lines) in a given text.

    Args:
        text (str): The input text.

    Returns:
        int: Paragraph count.
    """
    return len([p for p in text.split("\n") if p.strip()])


def get_merge_decision(client, slides):
    """
    Determines which two adjacent slides should be merged.

    Args:
        client (openai.OpenAI): OpenAI API client.
        slides (list): List of slide sections.

    Returns:
        list: Indices of the two adjacent sections to merge.
    """
    slide_metadata = [
        {
            "index": i,
            "words": count_words(slide),
            "paragraphs": count_paragraphs(slide),
            "text": slide
        }
        for i, slide in enumerate(slides)
    ]

    prompt = f"""
    ## **Task: Choose which sections to merge, return the indexes of those two sections**
    You are given a markdown document that has been split into sections, represented as a JSON list.
    Identify two adjacent sections that make the most sense to merge while maintaining balance in section sizes.
    The actual section is the value of "text" key.

    ## **Criteria**
    - Merge the two **smallest adjacent sections** based on **word count and paragraph count**.
    - Prioritize merging titles or very short sections into the section that follows over anything.
    - Ensure merged sections convey a coherent idea.

    ## **Current Sections**
    ```json
    {json.dumps(slide_metadata)}
    ```

    ## **Expected Output Format**
    ```json
    [0, 1]
    ```
    ### **You must only return the JSON and nothing else. No explanations. The sections start at index zero**
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert in document structuring."},
                  {"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
    return json.loads(json_response)


def get_split_decision(client, slides):
    """
    Determines which slide should be split.

    Args:
        client (openai.OpenAI): OpenAI API client.
        slides (list): List of slide sections.

    Returns:
        list: Index of the section to split.
    """
    slide_metadata = [
        {
            "index": i,
            "words": count_words(slide),
            "paragraphs": count_paragraphs(slide),
            "text": slide
        }
        for i, slide in enumerate(slides)
    ]

    prompt = f"""
    ## **Task: Choose which section to split, return the index of that section**
    You are given a markdown document that has been split into sections, represented as a JSON list.
    There are currently {len(slides)} sections, but we need {len(slides)+1} sections by splitting one.
    You are already provided with the number of words and paragraphs for each section.
    The actual section is the value of "text" key.

    ## **Criteria**
    - A section should be split based on size and amount of embedded discrete ideas.
    - The chosen section should contain distinct ideas that it makes more sense to split than other sections.

    ## **Current Sections**
    {json.dumps(slide_metadata)}

    ## **Expected Output Format**
    ```json
    [2]
    ```
    ### **You must only return the JSON and nothing else. No explanations. The sections start at index zero**
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert in document structuring."},
                  {"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
    return json.loads(json_response)


def split_slide(client, slide_text):
    """
    Calls the LLM to split a slide into two logical parts.

    Args:
        client (openai.OpenAI): OpenAI API client.
        slide_text (str): The text of the slide to be split.

    Returns:
        list: Two split sections as a list of strings.
    """
    prompt = f"""
    ## **Task: Split the following markdown text into 2 parts.
    
    ## **Criteria**
    - Aim for both parts to be roughlt equal in size.
    - The main criteria for the split is to separate distinct ideas.
    - If joined back together, the returned sections should match the original text.
    - You can not split mid sentence under any circumstance.

    TEXT:
    {slide_text}

    Return a JSON array of strings:
    ```json
    ["Part 1...", "Part 2..."]
    ```

    ### **You must only return the JSON and nothing else. No explanations. The sections start at index zero**
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert in document structuring."},
                  {"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content.replace("```json", "").replace("```", "")
    return json.loads(json_response)


def generate_slides(text, slides_target):
    """
    Generate slides from a given Markdown text while ensuring proper structuring.

    Args:
        text (str): The input Markdown content.
        slides_target (int): The desired number of slides.

    Returns:
        list: A list of slide sections as strings.
    """

    # Edge case: If only one slide is required, return the full text in a single-element list.
    if slides_target == 1:
        return [text.strip()]

    # Split on new lines and common sentence boundaries (. ! ?), keeping Markdown headings as separate slides.
    sentence_splits = re.split(r'(?<=[.!?])\s+|\n+', text.strip())

    # Edge case: If target slides exceed sentence count, return each sentence/heading as a slide.
    if slides_target >= len(sentence_splits):
        return [s.strip() for s in sentence_splits if s.strip()]  # Remove empty items.

    # Standard slide splitting based on headings.
    slides = headings_split(text)

    # For debugging and comparison between pre vs post ai processing
    #with open("output_by_headings.txt", "w", encoding="utf-8") as f:
    #    f.write("\n".join(f"Slide {i+1}:\n{slide}" for i, slide in enumerate(slides)))

    # Load OpenAI API key
    api_key = load_api_key()
    client = openai.OpenAI(api_key=api_key)

    # Adjust the slides until target is reached
    while len(slides) != slides_target:
        if len(slides) > slides_target:
            decision = get_merge_decision(client, slides)
            merge_index1, merge_index2 = sorted(decision)
            print(f"Merging slides {merge_index1} and {merge_index2}")
            slides[merge_index1] += "\n\n" + slides.pop(merge_index2)

        elif len(slides) < slides_target:
            decision = get_split_decision(client, slides)
            split_index = decision[0]
            print(f"Splitting slide {split_index}")
            target_slide = slides.pop(split_index)

            sections = split_slide(client, target_slide)
            slides.insert(split_index, sections[1].strip())
            slides.insert(split_index, sections[0].strip())

    return slides


def main():
    input_file = "input.md"
    slides_target = 14

    with open(input_file, "r", encoding="utf-8") as f:
        input_text = f.read()

    slides = generate_slides(input_text, slides_target)
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(f"Slide {i+1}:\n{slide}" for i, slide in enumerate(slides)))


if __name__ == "__main__":
    main()
