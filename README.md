# gamma-assignment
A Python program to convert a Markdown file into a list of sections by discrete ideas that can later be used for presentation slides. The program utilizes markdown headings and OpenAI gpt-4o-mini LLM for decision making.
## Setup Instructions
Install the packages
```
pip install -r requirements.txt
```
Create file `secrets.toml` and add your OpenAI API key, file contents should follow the format:
```toml
openai_key="abcde"
```
Run the program
```
python slides_gen.py
```
## Reasoning
I originally attempted a single prompt approach to see how LLM would perform, where I would create a single large comprehensive prompt, funnel the entire text, and ask to split into all necessary sections at once. No matter how comprehensive the prompt is, the model significantly hallucinates by creating a number of sections not even in the same realm of the target, and/or cut off the input text. Asking LLM to return a JSON list or the input text with embedded separators does not make a difference, both perform poorly. This is not surprising given LLM's sequential nature of token by token text generation. It is not able to have a proper awareness of all context at once in all parts of the input document, which is necessary to split into the exact requested number of slides. There was no point of using chained prompting either, since it would suffer from the same issues.

Therefore, my approach used a more localized LLM application. First, I split the input text into sections by Markdown headings. After that, we start splitting or merging the adjacent sections to reach the target number of slides. The LLM is used for both reasoning which slides to split/merge in round 1, and then to actually split a single slide in round 2, if necessary. This way the number of sections is strictly controlled by the code. When it comes to picking which section/sections to split/merge, the LLM receives a list of dictionaries containing the indexes of each section, and their metadata such as word count to take pressure off the LLM as much as possible. This way, the LLM only needs to generate a tiny JSON with the section numbers, significantly enhancing the speed of the code. Unfortunately, the LLM call for actually splitting a section still returns a JSON list with the actual section texts, this is something that has a room for improvement. Ideally, you would want the LLM to return an index-based breakpoint. When it comes to edge cases, I made it, so the target number of slides is capped by the total number of sentences and headings in the document, which in my opinion makes sense.