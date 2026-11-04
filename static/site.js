const menuButton=document.querySelector(".menu-toggle");
const mobileNav=document.querySelector(".mobile-nav");
if(menuButton&&mobileNav){
 const closeMenu=()=>{mobileNav.classList.remove("open");menuButton.setAttribute("aria-expanded","false");menuButton.setAttribute("aria-label","Open navigation")};
 menuButton.addEventListener("click",()=>{const open=mobileNav.classList.toggle("open");menuButton.setAttribute("aria-expanded",String(open));menuButton.setAttribute("aria-label",open?"Close navigation":"Open navigation")});
 mobileNav.querySelectorAll("a").forEach(a=>a.addEventListener("click",closeMenu));
 document.addEventListener("keydown",e=>{if(e.key==="Escape")closeMenu()});
 document.addEventListener("click",e=>{if(!mobileNav.contains(e.target)&&!menuButton.contains(e.target))closeMenu()});
}
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener("click",e=>{const target=document.querySelector(a.getAttribute("href"));if(target){e.preventDefault();target.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"})}}));
const views={
 baseline:{kicker:"BASELINE / C-1042",title:"The original obligation",copy:"A recorded starting point: what was agreed, by whom, and against which scope and date."},
 change:{kicker:"CHANGE EVENT / EVT-002",title:"The revision in context",copy:"A change is connected to the baseline and its approval source. If that source is absent, the gap remains visible for review."},
 delivery:{kicker:"DELIVERY EVENT / EVT-004",title:"The work reported as delivered",copy:"A handover or completion event is linked to the relevant obligation. Acceptance remains a separate question until supported."},
 evidence:{kicker:"SOURCE RECORD / DOC-008",title:"The record behind the finding",copy:"The original file, extracted text, source reference and integrity check stay connected to the event they support."}
};
const board=document.querySelector(".case-board");
document.querySelectorAll(".anatomy-tab").forEach(tab=>tab.addEventListener("click",()=>{
 const key=tab.dataset.view,view=views[key];if(!view)return;
 document.querySelectorAll(".anatomy-tab").forEach(t=>{const active=t===tab;t.classList.toggle("active",active);t.setAttribute("aria-selected",String(active))});
 if(board)board.dataset.active=key;
 const kicker=document.querySelector("#view-kicker"),title=document.querySelector("#view-title"),copy=document.querySelector("#view-copy");
 if(kicker)kicker.textContent=view.kicker;if(title)title.textContent=view.title;if(copy)copy.textContent=view.copy;
}));
