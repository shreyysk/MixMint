export async function safeEmail(fn: () => Promise<void>) {
    try {
        await fn();
    } catch (e) {
        console.error("[EMAIL_FAILURE]", e);
    }
}
