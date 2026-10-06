import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

// jsdom no implementa scrollTo / scrollIntoView.
window.scrollTo = () => {};
Element.prototype.scrollIntoView = () => {};
