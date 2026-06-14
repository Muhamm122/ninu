// Kapso Workflow Source Template
// Copy this to src/<your-slug>.ts and customize.
// Build with: npx tsx build-all.ts (which copies into workflows/<slug>/)
//
// Triggers reference a Kapso WhatsApp phone number ID. Get yours from:
//   kapso whatsapp numbers list

import { START, Workflow } from "@kapso/workflows";

// === Configuration ===
const PHONE_ID = "597907523413541";  // your WhatsApp phone_number_id

// === Workflow definition ===
const workflow = new Workflow("my-workflow", {
  name: "My Workflow Display Name",
  status: "active",
});

// === Trigger (pick one) ===

// A) Inbound message — fires on any incoming WhatsApp message
workflow.addTrigger({
  type: "inbound_message",
  phoneNumberId: PHONE_ID,
  active: true,
});

// B) API call — fires on POST to the workflow's API endpoint
// workflow.addTrigger({
//   type: "api_call",
//   active: true,
// });

// C) WhatsApp event — fires on platform events (UNSTABLE — see references/kapso-workflow-deployment.md §5)
// workflow.addTrigger({
//   type: "whatsapp_event",
//   event: "message.delivered",  // event name — must be in kapso allowlist, otherwise 422
//   phoneNumberId: PHONE_ID,
//   active: true,
// });

// === Nodes ===

workflow.addNode(START, {
  position: { x: 100, y: 100 },
});

workflow.addNode("send-greeting", {
  type: "send_text",
  message: "👋 Hello! Reply with anything to continue.",
  saveResponseTo: "greeting_sent",
});

workflow.addNode("log-event", {
  type: "set_variable",
  variableName: "received_at",
  variableValue: "now",
  valueType: "string",
  saveResponseTo: "event_logged",
});

workflow.addNode("wait-reply", {
  type: "wait_for_response",
  timeoutSeconds: 3600,  // 1h
});

workflow.addNode("send-thanks", {
  type: "send_text",
  message: "✅ Thanks for your reply!",
  saveResponseTo: "thanks_sent",
});

// === Edges ===
workflow.addEdge(START, "send-greeting");
workflow.addEdge("send-greeting", "log-event");
workflow.addEdge("log-event", "wait-reply");
workflow.addEdge("wait-reply", "send-thanks");

// === Exports (kapso CLI requires `export default workflow`) ===
const { metadata, definition, definitionJson } = workflow.toSourceFiles();
export { metadata, definition, definitionJson };
export default workflow;
