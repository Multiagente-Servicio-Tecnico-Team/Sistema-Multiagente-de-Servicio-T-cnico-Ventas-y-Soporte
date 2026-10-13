export function resolveApiBaseUrl(
  configuredUrl,
  productionFallback,
  isProduction = false,
) {
  const configured = typeof configuredUrl === "string" ? configuredUrl.trim() : "";
  if (!isProduction) return configured;
  if (!configured || /^(?:[a-z][a-z\d+.-]*:)?\/\//i.test(configured)) {
    return productionFallback;
  }
  return configured;
}
