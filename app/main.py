from langchain_core.messages import HumanMessage

from app.agents.graph import build_graph, new_thread_id
from app.database.repository import find_user_by_email


def main() -> None:
    email = input("Email del usuario registrado: ").strip()
    if not email:
        print("El email es obligatorio.")
        return

    user = find_user_by_email(email)
    if user is None:
        print("No existe un usuario con ese email. Regístralo en la base de datos primero.")
        return

    graph = build_graph()
    thread_id = new_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    print(
        f"Sesión de autenticación simulada para {user.get('nombre', user.get('name', email))}. "
        "Escribe 'salir' para terminar."
    )

    while True:
        prompt = input("Tú: ").strip()
        if prompt.casefold() in {"salir", "exit", "quit"}:
            break
        if not prompt:
            continue

        result = graph.invoke(
            {
                "messages": [HumanMessage(content=prompt)],
                "user_id": user["id"],
            },
            config=config,
        )
        print(f"\nAtención: {result['response']}\n")
        if not result.get("awaiting_clarification"):
            break


if __name__ == "__main__":
    main()