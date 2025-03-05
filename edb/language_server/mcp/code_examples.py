from .types import CodeExample


code_examples = []

code_examples.append(
    CodeExample(
        slug="schema-ai",
        description="An example schema that uses the AI extension to automatically generate embedding vectors for a type",
        language="gel",
        code="""
module default {
    type Friend {
        required name: str {
            constraint exclusive;
        };

        summary: str;               # A brief description of personality and role
        relationship_to_komi: str;  # Relationship with Komi
        defining_trait: str;        # Primary character trait or quirk

        deferred index ext::ai::index(embedding_model := 'text-embedding-3-small')
            on (
                .name ++ ' ' ++ .summary ++ ' '
                ++ .relationship_to_komi ++ ' '
                ++ .defining_trait
            );
    }
}
""".strip(),
    )
)

code_examples.append(
    CodeExample(
        slug="python-query-ai",
        description="Example Python code that uses Gel AI Python binding to perform similarity search for a text query",
        language="python",
        code="""
import gel
import gel.ai

gel_client = gel.create_client()
gel_ai = gel.ai.create_rag_client(client)

text = "Who helps Komi make friends?"
vector = gel_ai.generate_embeddings(
    text,
    "text-embedding-3-small",
)

gel_client.query(
    "select ext::ai::search(Friend, <array<float32>>$embedding_vector",
    embedding_vector=vector,
)
""".strip(),
    )
)
