# Evidencia 10 — proxy de API desde Netlify

## Cambio

Se agregó `landing/public/_redirects` para enviar `/backend/*` desde Netlify
hacia la API unificada de Render. La segunda regla conserva el fallback de
rutas de la SPA. Al estar el archivo en `public/`, Vite lo copia al directorio
de publicación `dist/`.

Para activar el proxy en el sitio de Netlify, configurar antes del build:

```env
VITE_API_URL=/backend/auth
VITE_CHAT_URL=/backend
```

El origen del sitio Netlify debe estar incluido en `FRONTEND_ORIGINS` del
backend Render. Después de actualizar esas variables, se debe reconstruir y
volver a publicar el frontend, cerrar sesión e iniciar una sesión nueva.

## Validación

Se verifica con `npm --prefix landing run build` que Vite publica
`dist/_redirects` junto con los recursos estáticos. La propagación HTTP de las
reglas requiere un deploy real en Netlify y no se considera probada localmente.
