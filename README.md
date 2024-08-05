# LL-DM: a barebones LLM-powered DnD Dungeon Master showcasing the power of LLM4LLM

## When it comes to long-term AI assistants, LLMS have some problems [[1]](#1)...

- Token limits can lead to truncated context.
- Information overload can muddy language understanding.
- Small details can be lost as conversations get long.
- Distant events may be easily subject to hallucination.
- Processing time significantly increases as context window gets larger

How can we augment conversations with LLMs to improve long-term memory while still maintaining the seamless experience of having a conversation that modern LLMs excel at?

## What is LLM4LLM?

Longer-Lasting Memory for Large Language Models (LLM4LLM) is a framework that leverages structured memory systems such as SQL databases to store and retrieve memory points while conversion with an LLM assistant. 

By leveraging the everlasting information persistence of structured databases in conjunction with LLMs' function calling abilities, LLM4LLM allows large language models to maintain memory points indefinitely, regardless of the conversation length or complexity. There are many customizable steps that users can add on, including extra functions to perform , validation and security checks to maintain data integrity, or reference tables to constrain user input.

For our testing purposes, we implemented an assistant reminiscent of a **Dungeons & Dragons dungeon master**, which allows ample opportunity to both progress a long-term story, as well as provides a perfect vehicle for testing long-term memory using **inventory management**.

## To learn more, visit our webpage!

[LLM4LLM info page](https://kdai11830.github.io/ll-dm/)

## References
<a id="1">[1]</a> 
Hatalis et al. (2024). 
Memory Matters: The Need to Improve Long-Term Memory in LLM-Agents.
Vol. 2 No. 1: Proceedings of the 2023 AAAI Fall Symposia.
https://doi.org/10.1609/aaaiss.v2i1.27688