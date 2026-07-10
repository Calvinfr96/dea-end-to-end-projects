let innerBody;

try {
  // 1. Parse the main incoming payload text
  const payload = JSON.parse(inputData.rawBody);
  
  // 2. Safely check if it's wrapped in an AWS/API Gateway "body" string
  if (payload.body && typeof payload.body === 'string') {
    innerBody = JSON.parse(payload.body);
  } else {
    // If it's already unwrapped (like your most recent request), use it directly
    innerBody = payload;
  }
} catch (e) {
  throw new Error("Could not parse incoming data. Check if rawBody is valid JSON.");
}

// 3. Extract the lead_id and clean payload safely
output = { 
  lead_id: innerBody.event ? innerBody.event.lead_id : "unknown_lead",
  fullCleanJson: innerBody
};
