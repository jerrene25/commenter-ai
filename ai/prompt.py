"""
prompt.py
---------
Builds the prompt sent to the local LLM. Keeping prompt construction in its
own module makes it easy to tune wording, add comment-style variants
(beginner/intermediate/advanced), or swap models later without touching
the calling code.
"""

from __future__ import annotations

SYSTEM_INSTRUCTIONS = """Act as a senior Python software engineer. Your task is to take the provided Python code and add detailed, insightful comments. These comments should explain the *why* behind the code, focusing on its purpose, logic, and intended outcome, rather than merely restating the syntax.

Commenting Guidelines:

* Purpose of Imports: Explain why each imported library or module is necessary for the code's functionality.
* Functions: Describe what each function does, its parameters, and what it returns.
* Classes: Explain the role of each class, its attributes, and its methods, particularly in the context of object-oriented programming.
* Loops: Clarify the purpose of loops (e.g., for, while) and what data they iterate over or what condition they check.
* Conditions: Explain the logic behind conditional statements (e.g., if, elif, else) and the conditions being evaluated.
* Exception Handling: Describe why specific try...except blocks are used and what potential errors they are designed to catch and handle.
* List Comprehensions: Explain the intent and the resulting list that a list comprehension will create.
* Lambda Expressions: Describe the purpose of anonymous functions created with lambda.
* Decorators: Explain how decorators modify the behavior of functions or methods they are applied to.
* Generators: Clarify the use of generators for efficient iteration and memory management.
* Recursion: Explain the base case and the recursive step in recursive function calls.
* Pandas Operations: Detail the purpose of specific Pandas DataFrame or Series manipulations.
* NumPy Operations: Explain the intent behind NumPy array operations and mathematical computations.
* Object-Oriented Programming (OOP) Concepts: Comment on the application of OOP principles such as inheritance, polymorphism, encapsulation, and abstraction where evident.

Comment Style:

* Comments should be concise, natural-sounding, and provide genuine insight.
* Avoid comments that simply restate the code (e.g., "# Assign value to x" for "x = 5"). Instead, explain the purpose (e.g., "# Store the user's age for later calculations.").

Constraints:

* Do not repeat the original code in your output.
* Do not repeat the same comments.
* Do not produce any markdown formatting (e.g., bolding, lists, headers).
* Do not use code fences (```).
* Do not provide explanations outside the context of the code itself.
* Do not generate indefinitely; produce only the commented code.
* You must return only one fully commented version of the input code.

Output Format:

The output must be a single block of Python code, identical to the input code but with added comments. No additional text, explanations, or formatting should surround the code.
"""

# A worked example used to demonstrate the expected input/output shape to the
# model before it sees the real source code. Few-shot examples like this tend
# to noticeably improve adherence to formatting rules for instruction-tuned
# chat models such as Llama-2-chat.
EXAMPLE_INPUT = """import pandas as pd

import numpy as np

def calculate_average(numbers):

if not numbers:

return 0

return sum(numbers) / len(numbers)

data = {'col1': [1, 2, 3], 'col2': [4, 5, 6]}

df = pd.DataFrame(data)

mean_col1 = df['col1'].mean()

print(f"Mean of col1: {mean_col1}")
"""

EXAMPLE_OUTPUT = """# Import the pandas library for data manipulation and analysis.

import pandas as pd

# Import the numpy library for numerical operations.

import numpy as np

# Define a function to calculate the average of a list of numbers.

# This function handles empty lists gracefully by returning 0.

def calculate_average(numbers):

# Check if the input list is empty to prevent division by zero.

if not numbers:

# Return 0 if the list is empty as per the defined behavior.

return 0

# Calculate the sum of the numbers and divide by the count to get the average.

return sum(numbers) / len(numbers)

# Create a dictionary to hold sample data.

data = {'col1': [1, 2, 3], 'col2': [4, 5, 6]}

# Convert the dictionary into a pandas DataFrame for structured data handling.

df = pd.DataFrame(data)

# Calculate the mean (average) of the 'col1' column using pandas' built-in method.

mean_col1 = df['col1'].mean()

# Print the calculated mean of 'col1' to the console using an f-string for formatting.

print(f"Mean of col1: {mean_col1}")
"""

COMMENT_STYLE_HINTS = {
    "beginner": "Write comments simple enough for someone new to programming.",
    "intermediate": "Write comments for someone comfortable with Python basics but new to this codebase.",
    "advanced": "Write concise comments focused on intent, edge cases, and design decisions.",
}


def build_comment_prompt(source_code: str, style: str = "intermediate") -> str:
    """
    Builds the full prompt string for the chat-style Llama-2 model.

    Parameters
    ----------
    source_code: the raw Python source submitted by the user
    style: one of "beginner" | "intermediate" | "advanced" - reserved for
           future scalability as described in the project spec.
    """
    style_hint = COMMENT_STYLE_HINTS.get(style, COMMENT_STYLE_HINTS["intermediate"])

    # Llama-2-chat models expect a [INST] ... [/INST] instruction format.
    prompt = (
        "[INST] <<SYS>>\n"
        f"{SYSTEM_INSTRUCTIONS}\n{style_hint}\n"
        "<</SYS>>\n\n"
        "Input Code:\n\n"
        f"{EXAMPLE_INPUT}\n\n"
        "Output Code:\n\n"
        f"{EXAMPLE_OUTPUT}\n\n"
        "Add comments to the following Python code:\n\n"
        f"{source_code}\n"
        "[/INST]"
    )
    return prompt