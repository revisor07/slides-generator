# gamma-assignment
A Python program to convert a Markdown file into a list of sections by discrete ideas that can later be used for presentation slides. The program utilizes markdown headings and OpenAI gpt-4o-mini LLM for decision making.
## Setup Instructions
1. Install the packages
```
pip install -r requirements.txt
```
2. Create file `secrets.toml` and add your OpenAI API key, file contents should follow the format:
```toml
openai_key="abcde"
```
3. Insert your markdown input into `input.md` file

4. Run the program
```
python slides_gen.py
```
## Notes
First, the input text is split into sections by Markdown headings. After that, we start splitting or merging the adjacent sections to reach the target number of slides. The LLM is used for both reasoning which slides to split/merge in round 1, and then to actually split a single slide in round 2, if necessary. This way the number of sections is strictly controlled by the code. When it comes to picking which slides to split or merge, the LLM receives a list of dictionaries containing the indexes of each section and the actual slide. Also, LLM received the metadata such as the word count to take as much unnecessary pressure off LLM as possible. With this approach, the LLM only needs to generate a tiny JSON with the section numbers, significantly enhancing the speed of the program. Unfortunately, the LLM call for actually splitting a section in the current iteration returns a JSON list with the full slides, this is something that has a room for improvement. Ideally, you would want the LLM to return an index-based breakpoint. When it comes to edge cases, the target number of slides is capped by the total number of sentences and headings in the document. If the initial slide count resulting after splitting by the markdown heading equals to the target, then no LLM is invoked. Lastly, If the target number of slides equal to 1, then we return the original text before markdown or LLM splitting.