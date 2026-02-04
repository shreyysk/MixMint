import { logger } from "./logger";

export function ok(data: any = {}, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

export function fail(message: string, status = 400, tag: any = "SYSTEM") {
    // Automatically log failures for observability
    if (status >= 500) {
        logger.error(tag, `Server Error: ${message}`, { status });
    } else if (status >= 400) {
        logger.warn(tag, `Client Error: ${message}`, { status });
    }

    return new Response(JSON.stringify({ error: message }), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}
