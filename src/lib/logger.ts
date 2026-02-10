/**
 * MixMint Structured Logger
 * Standardizes log format with domain tags for better observability.
 */

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR" | "ALERT";
type DomainTag = "AUTH" | "PAYMENT" | "DOWNLOAD" | "UPLOAD" | "REWARDS" | "SYSTEM" | "CRON" | "ADMIN" | "SECURITY";


interface LogPayload {
    level: LogLevel;
    tag: DomainTag;
    message: string;
    context?: any;
    timestamp: string;
}

class Logger {
    private isProd = process.env.NODE_ENV === "production";

    private format(level: LogLevel, tag: DomainTag, message: string, context?: any): string {
        const payload: LogPayload = {
            level,
            tag,
            message,
            context,
            timestamp: new Date().toISOString(),
        };

        // In local env, we can make it pretty; in prod, we usually want JSON for log aggregators
        if (!this.isProd) {
            const colorMap = {
                DEBUG: "\x1b[36m", // Cyan
                INFO: "\x1b[32m",  // Green
                WARN: "\x1b[33m",  // Yellow
                ERROR: "\x1b[31m", // Red
                ALERT: "\x1b[35m\x1b[1m", // Bold Magenta
            };
            const reset = "\x1b[0m";
            const color = (colorMap as any)[level] || reset;

            return `${color}[${level}] [${tag}]${reset} ${message} ${context ? JSON.stringify(context, null, 2) : ""}`;
        }

        return JSON.stringify(payload);
    }

    debug(tag: DomainTag, message: string, context?: any) {
        if (!this.isProd) {
            console.debug(this.format("DEBUG", tag, message, context));
        }
    }

    info(tag: DomainTag, message: string, context?: any) {
        console.info(this.format("INFO", tag, message, context));
    }

    warn(tag: DomainTag, message: string, context?: any) {
        console.warn(this.format("WARN", tag, message, context));
    }

    error(tag: DomainTag, message: string, error?: any, context?: any) {
        // If it's an Error object, extract info
        const errorInfo = error instanceof Error ? {
            name: error.name,
            message: error.message,
            stack: error.stack,
        } : error;

        console.error(this.format("ERROR", tag, message, { ...context, error: errorInfo }));

        // Centralized Error Monitoring Hook (e.g. Sentry) can be added here
        if (this.isProd) {
            // Example: Sentry.captureException(error);
        }
    }

    /**
     * High-priority alerts that should trigger notifications (Slack, Discord, PagerDuty etc.)
     */
    alert(tag: DomainTag, message: string, context?: any) {
        const logOutput = this.format("ALERT", tag, message, context);
        console.error(logOutput);

        // CRITICAL: Trigger external notification hooks here
        if (this.isProd) {
            // Example: this.triggerDiscordWebhook(message, tag, context);
        }
    }
}

export const logger = new Logger();
