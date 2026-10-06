from typing import Any

from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.jerarquico.knowledge_retrieval import (
    make_knowledge_retrieval_agent,
)
from app.agents.jerarquico.persistence import (
    customer_care_response,
    make_persist_quote,
)
from app.agents.jerarquico.retriever import MarkdownKnowledgeRetriever
from app.agents.jerarquico.sales import make_sales_agent, quote_suggestion_response
from app.agents.jerarquico.supervisor import make_customer_care_supervisor
from app.agents.jerarquico.technical_support import make_technical_support_agent
from app.agents.jerarquico.warehouse import make_warehouse_agent
from app.database.repository import ServiceRepository
from app.agents.jerarquico.graph.routing import (
    after_inventory,
    after_sales,
    after_supervisor,
)
from app.agents.jerarquico.graph.state import ServiceState
from app.settings import Settings, load_settings


def build_multiagent_graph(
    *,
    settings: Settings | None = None,
    repository: ServiceRepository | None = None,
    model: Any | None = None,
    retriever: MarkdownKnowledgeRetriever | None = None,
):
    settings = settings or load_settings()
    settings.require_chat_configuration()
    repository = repository or ServiceRepository()
    retriever = retriever or MarkdownKnowledgeRetriever()
    llm = model or ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )

    graph = StateGraph(ServiceState)
    graph.add_node(
        "customer_care_supervisor",
        make_customer_care_supervisor(llm, repository),
    )
    graph.add_node(
        "knowledge_retrieval",
        make_knowledge_retrieval_agent(retriever),
    )
    graph.add_node(
        "technical_support_agent",
        make_technical_support_agent(llm),
    )
    graph.add_node("warehouse_agent", make_warehouse_agent(repository))
    graph.add_node("sales_agent", make_sales_agent(settings))
    graph.add_node("quote_suggestion_response", quote_suggestion_response)
    graph.add_node("persist_quote", make_persist_quote(repository, settings))
    graph.add_node("customer_care_response", customer_care_response)

    graph.add_edge(START, "customer_care_supervisor")
    graph.add_conditional_edges(
        "customer_care_supervisor",
        after_supervisor,
        {
            "knowledge_retrieval": "knowledge_retrieval",
            "warehouse_agent": "warehouse_agent",
            END: END,
        },
    )
    graph.add_edge("knowledge_retrieval", "technical_support_agent")
    graph.add_edge("technical_support_agent", "warehouse_agent")
    graph.add_conditional_edges(
        "warehouse_agent",
        after_inventory,
        {
            "sales_agent": "sales_agent",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "sales_agent",
        after_sales,
        {
            "persist_quote": "persist_quote",
            "quote_suggestion_response": "quote_suggestion_response",
        },
    )
    graph.add_edge("quote_suggestion_response", END)
    graph.add_edge("persist_quote", "customer_care_response")
    graph.add_edge("customer_care_response", END)

    return graph.compile(checkpointer=InMemorySaver())
