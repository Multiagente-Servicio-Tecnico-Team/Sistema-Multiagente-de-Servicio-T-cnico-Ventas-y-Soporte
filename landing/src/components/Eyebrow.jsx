export default function Eyebrow({ children, dot = true, tone = "blue", center = false }) {
  return (
    <p className={`eyebrow eyebrow--${tone}${center ? " eyebrow--center" : ""}`}>
      {dot && <span className="eyebrow__dot" aria-hidden="true" />}
      {children}
    </p>
  );
}
