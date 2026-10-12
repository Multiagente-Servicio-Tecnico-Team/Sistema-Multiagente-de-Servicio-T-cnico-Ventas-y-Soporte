import { Link } from "react-router-dom";

export default function Logo({ to = "/" }) {
  return (
    <Link to={to} className="logo" aria-label="TechFix.AI inicio">
      <span className="logo__mark" aria-hidden="true">
        A<span className="logo__dot" />
      </span>
      <span className="logo__text">
        TechFix<span className="logo__ai">.AI</span>
      </span>
    </Link>
  );
}
