import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * Calculates the revenue split between the DJ and the Platform.
 * Default is 80% to DJ, 20% to Platform.
 */
export async function calculateRevenueSplit(djId: string, totalAmount: number) {
    try {
        const { data: settings } = await supabaseServer
            .from("monetization_settings")
            .select("revenue_share_pct")
            .eq("dj_id", djId)
            .single();

        const djSharePct = settings?.revenue_share_pct || 88.00;
        const djAmount = (totalAmount * djSharePct) / 100;
        const platformAmount = totalAmount - djAmount;

        return {
            djAmount,
            platformAmount,
            djSharePct,
        };
    } catch (err) {
        logger.warn("SYSTEM", "Failed to fetch monetization settings, using defaults", { djId });
        const djAmount = (totalAmount * 88) / 100;
        return {
            djAmount,
            platformAmount: totalAmount - djAmount,
            djSharePct: 88,
        };
    }
}
/**
 * Records a revenue event in the wallet and ledger.
 */
export async function recordRevenue(djId: string, amount: number, type: 'track_sale' | 'zip_sale' | 'subscription', referenceId: string) {
    try {
        const split = await calculateRevenueSplit(djId, amount);

        // 1. Update DJ Wallet
        const { error: walletErr } = await supabaseServer.rpc('increment_wallet_balance', {
            target_id: djId,
            amount: split.djAmount
        });

        if (walletErr) throw walletErr;

        // 2. Create Ledger Entries
        await supabaseServer.from('ledger_entries').insert([
            {
                wallet_id: djId,
                amount: split.djAmount,
                type: 'credit',
                description: `Revenue from ${type} (${referenceId})`,
                metadata: { ...split, reference_id: referenceId, type }
            }
        ]);

        return split;
    } catch (err) {
        logger.error("SYSTEM", "Failed to record revenue", err, { djId, amount });
        throw err;
    }
}
/**
 * Generates an invoice and tax records for a purchase.
 */
export async function generateInvoice(purchaseId: string) {
    try {
        const { data: purchase, error: purchaseErr } = await supabaseServer
            .from('purchases')
            .select('*, profiles(full_name), tracks(title, dj_id, price), album_packs(title, dj_id, price)')
            .eq('id', purchaseId)
            .single();

        if (purchaseErr || !purchase) throw new Error("Purchase not found");

        const djId = purchase.tracks?.dj_id || purchase.album_packs?.dj_id;
        const subtotal = purchase.amount_paid;
        const taxRate = 18; // Default GST for India, should be dynamic in prod
        const taxAmount = (subtotal * taxRate) / 100;
        const totalAmount = subtotal + taxAmount;

        const invoiceNumber = `INV-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

        const { data: invoice, error: invoiceErr } = await supabaseServer
            .from('invoices')
            .insert({
                purchase_id: purchaseId,
                user_id: purchase.user_id,
                dj_id: djId,
                invoice_number: invoiceNumber,
                subtotal,
                tax_amount: taxAmount,
                total_amount: totalAmount,
                status: 'issued'
            })
            .select()
            .single();

        if (invoiceErr) throw invoiceErr;

        // Create Tax Record
        await supabaseServer.from('tax_records').insert({
            invoice_id: invoice.id,
            tax_type: 'GST',
            tax_rate: taxRate,
            tax_amount: taxAmount,
            jurisdiction: 'India'
        });

        return invoice;
    } catch (err) {
        logger.error("SYSTEM", "Failed to generate invoice", err, { purchaseId });
    }
}
