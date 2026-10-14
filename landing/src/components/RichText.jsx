// Muestra el texto del agente con **negritas**. Se arma con elementos de React (sin HTML),
// así que cualquier etiqueta que venga en la respuesta se ve como texto.
const BOLD = /\*\*(.+?)\*\*/g;

export default function RichText({ text }) {
  const value = String(text ?? "");
  const parts = [];
  let last = 0;
  for (const match of value.matchAll(BOLD)) {
    if (match.index > last) parts.push(value.slice(last, match.index));
    parts.push(<strong key={match.index}>{match[1]}</strong>);
    last = match.index + match[0].length;
  }
  parts.push(value.slice(last));
  return <>{parts}</>;
}
