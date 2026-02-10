'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';

/**
 * useExperiment Hook
 * Fetches an active experiment and assigns/retrieves a variant for the user.
 * 
 * @param experimentName The name of the experiment to track
 * @param variants Array of variant names (e.g., ['control', 'variant_a'])
 */
export function useExperiment(experimentName: string, variants: string[] = ['control', 'variant_a']) {
    const [variant, setVariant] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchExperiment() {
            try {
                // 1. Get active experiment by name
                const { data: exp, error } = await supabase
                    .from('experiments')
                    .select('*')
                    .eq('name', experimentName)
                    .eq('status', 'running')
                    .single();

                if (error || !exp) {
                    setVariant('control');
                    setLoading(false);
                    return;
                }

                // 2. Consistent Hashing or Sticky Selection
                // For now, we'll do a simple random selection if not already logged, 
                // in production this should ideally be handled at the Edge or via sticky cookie/profile.
                let selectedVariant = 'control';
                
                // Check if user is logged in
                const { data: { session } } = await supabase.auth.getSession();
                const userId = session?.user?.id;

                if (userId) {
                    // Check if user already has an exposure record
                    const { data: existing } = await supabase
                        .from('experiment_exposures')
                        .select('variant_name')
                        .eq('experiment_id', exp.id)
                        .eq('user_id', userId)
                        .single();

                    if (existing) {
                        selectedVariant = existing.variant_name;
                    } else {
                        // Assign new random variant
                        selectedVariant = variants[Math.floor(Math.random() * variants.length)];
                        
                        // Record exposure
                        await supabase.from('experiment_exposures').insert({
                            experiment_id: exp.id,
                            user_id: userId,
                            variant_name: selectedVariant
                        });
                    }
                } else {
                    // Anonymous user - just random for session
                    selectedVariant = variants[Math.floor(Math.random() * variants.length)];
                }

                setVariant(selectedVariant);
            } catch (err) {
                console.error('[USE_EXPERIMENT_ERROR]', err);
                setVariant('control');
            } finally {
                setLoading(false);
            }
        }

        fetchExperiment();
    }, [experimentName, variants]);

    return { variant, loading };
}
