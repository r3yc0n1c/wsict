"use server";

import { supabase } from "@/lib/supabase";

export async function incrementMetric(projectName: string = "wsict", metricName: string) {
  try {
    const { error } = await supabase.rpc("increment_metric", {
      target_project: projectName,
      target_metric: metricName,
    });

    if (error) {
      console.warn("RPC increment_metric warning, using fallback table update:", error.message);
      const { data: row } = await supabase
        .from("project_metrics")
        .select("value")
        .eq("project_id", projectName)
        .eq("metric_name", metricName)
        .single();

      if (row) {
        await supabase
          .from("project_metrics")
          .update({
            value: (row.value || 0) + 1,
            updated_at: new Date().toISOString(),
          })
          .eq("project_id", projectName)
          .eq("metric_name", metricName);
      }
    }
  } catch (err) {
    console.error("Failed to increment metric:", err);
  }
}

export async function incrementMetricBy(
  projectName: string = "wsict",
  metricName: string,
  amount: number,
) {
  try {
    const { error } = await supabase.rpc("increment_metric", {
      target_project: projectName,
      target_metric: metricName,
    });

    const { data: row } = await supabase
      .from("project_metrics")
      .select("value")
      .eq("project_id", projectName)
      .eq("metric_name", metricName)
      .single();

    if (row) {
      // If RPC failed or only added 1, ensure the exact batch amount is counted
      const nextValue = error
        ? (row.value || 0) + amount
        : Math.max(row.value || 0, (row.value || 0) + amount - 1);
      await supabase
        .from("project_metrics")
        .update({
          value: nextValue,
          updated_at: new Date().toISOString(),
        })
        .eq("project_id", projectName)
        .eq("metric_name", metricName);
    }
  } catch (err) {
    console.error("Failed to increment metric by amount:", err);
  }
}

export async function getMetrics(projectName: string = "wsict") {
  try {
    const { data, error } = await supabase
      .from("project_metrics")
      .select("metric_name, value")
      .eq("project_id", projectName);

    if (error || !data) {
      return { visitors: 0, total_generated_names: 0 };
    }

    const result: Record<string, number> = {
      visitors: 0,
      total_generated_names: 0,
    };

    for (const item of data) {
      result[item.metric_name] = item.value || 0;
    }

    return result;
  } catch (err) {
    console.error("Failed to get metrics:", err);
    return { visitors: 0, total_generated_names: 0 };
  }
}

export async function checkLlmStatus(): Promise<{ online: boolean; model?: string }> {
  try {
    const rawUrl = process.env.LLM_API_BASE_URL!;
    const apiKey = process.env.LLM_API_KEY!;
    const model = process.env.LLM_MODEL!;

    let healthUrl = `${rawUrl}/health`;
    
    const headers: Record<string, string> = {};
    if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
    if (process.env.CF_ACCESS_CLIENT_ID) {
      headers["CF-Access-Client-Id"] = process.env.CF_ACCESS_CLIENT_ID;
      headers["CF-Access-Client-Secret"] = process.env.CF_ACCESS_CLIENT_SECRET || "";
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);

    try {
      const res = await fetch(healthUrl, {
        method: "GET",
        headers,
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeout);
      if (res.ok) {
        return { online: true, model };
      }
    } catch {
      // Fallback to checking models endpoint
    }

    const modelsUrl = rawUrl.replace(/\/chat\/completions\/?$/, "/models");
    const controller2 = new AbortController();
    const timeout2 = setTimeout(() => controller2.abort(), 2500);
    const res2 = await fetch(modelsUrl, {
      method: "GET",
      headers,
      signal: controller2.signal,
      cache: "no-store",
    });
    clearTimeout(timeout2);

    return { online: res2.ok, model };
  } catch {
    return { online: false };
  }
}
