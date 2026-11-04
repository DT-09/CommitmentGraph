// Evidence linking and authenticated exports for the production interface.
async function commitmentForm(){
  try{state.evidence=await api("/api/evidence")}catch(e){toast(e.message);return}
  const sourceOptions='<option value="">No source linked</option>'+state.evidence.map(d=>'<option value="'+esc(d.id)+'">'+esc(d.filename)+' · '+esc(d.id)+'</option>').join("");
  openModal("New commitment",'<form id="commitment-form"><div class="form-grid"><div class="form-field full"><label>Commitment title *</label><input name="title" required maxlength="300" placeholder="e.g. Deliver revised pump assembly specification"></div><div class="form-field"><label>Counterparty</label><input name="counterparty" placeholder="Customer or supplier"></div><div class="form-field"><label>Owner</label><input name="owner" placeholder="Internal accountable owner"></div><div class="form-field"><label>Status</label><select name="status"><option value="open">Open</option><option value="in_progress">In progress</option><option value="blocked">Blocked</option><option value="fulfilled">Fulfilled</option><option value="cancelled">Cancelled</option></select></div><div class="form-field"><label>Due date</label><input name="due_date" type="date"></div><div class="form-field"><label>Value</label><input name="value" type="number" min="0" step=".01" placeholder="0.00"></div><div class="form-field"><label>Currency</label><input name="currency" value="USD" maxlength="3"></div><div class="form-field full"><label>Supporting source record</label><select name="source_id">'+sourceOptions+'</select></div><div class="form-field full"><label>Description / acceptance criteria</label><textarea name="description" placeholder="Describe the exact obligation and what constitutes fulfilment."></textarea></div></div><div class="form-actions"><button type="button" class="btn btn-quiet" id="cancel-modal">Cancel</button><button class="btn btn-primary">Create commitment</button></div></form>');
  $("#commitment-form").addEventListener("submit",async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.value=d.value?Number(d.value):null;d.due_date=d.due_date||null;d.source_id=d.source_id||null;try{await api("/api/commitments",{method:"POST",body:JSON.stringify(d)});closeModal();toast("Commitment created.");await loadCommitments();navigate(state.view==="overview"?"overview":"commitments")}catch(err){toast(err.message)}});
  $("#cancel-modal").onclick=closeModal;
}
async function eventModal(id){
  try{state.evidence=await api("/api/evidence")}catch(e){toast(e.message);return}
  const sourceOptions='<option value="">No source linked</option>'+state.evidence.map(d=>'<option value="'+esc(d.id)+'">'+esc(d.filename)+' · '+esc(d.id)+'</option>').join("");
  openModal("Record commitment event",'<form id="event-form"><div class="form-field"><label>Event type</label><select name="event_type"><option value="scope_change">Scope change</option><option value="amendment">Amendment</option><option value="requirement_change">Requirement change</option><option value="delivery">Delivery</option><option value="handover">Handover</option><option value="acceptance">Acceptance</option><option value="invoice">Invoice / billing</option><option value="note">Other note</option></select></div><div class="form-field"><label>Description *</label><textarea name="description" required></textarea></div><div class="form-field"><label>Occurred at</label><input type="datetime-local" name="occurred_at"></div><div class="form-field"><label>Supporting source record</label><select name="source_id">'+sourceOptions+'</select></div><div class="form-field"><label><input type="checkbox" name="approved" value="true" style="width:auto"> Approval evidence reviewed</label></div><div class="form-actions"><button type="button" class="btn btn-quiet" id="cancel-modal">Cancel</button><button class="btn btn-primary">Save event</button></div></form>');
  $("#event-form").addEventListener("submit",async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));d.approved=!!e.target.approved.checked;d.source_id=d.source_id||null;d.occurred_at=d.occurred_at?new Date(d.occurred_at).toISOString():null;try{await api("/api/commitments/"+id+"/events",{method:"POST",body:JSON.stringify(d)});closeModal();toast("Event recorded.");await loadCommitments()}catch(err){toast(err.message)}});
  $("#cancel-modal").onclick=closeModal;
}
document.addEventListener("click",async e=>{
  const link=e.target.closest("a.download-link");
  if(!link)return;
  e.preventDefault();
  try{
    const response=await fetch(link.href,{headers:{"x-api-key":apiKey()}});
    if(!response.ok)throw new Error("Export failed ("+response.status+"). Check the API key.");
    const blob=await response.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");a.href=url;
    a.download=link.href.endsWith(".csv")?link.href.split("/").pop():"commitmentgraph-graph.json";
    document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
  }catch(err){toast(err.message)}
},true);
