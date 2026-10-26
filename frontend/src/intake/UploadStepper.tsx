import {routeLink, type Route} from '../routing';
import type {StepState, StepStatus, UploadStep} from './stepper';

const STATE_TEXT:Record<StepState,string>={done:'Done',current:'Next',todo:'To do',attention:'Needs your review'};

// Vertical six-step stepper. Each step is a plain link, so the owner can jump to any step freely;
// the viewed step is marked aria-current="step", and the state words come from saved workspace data.
export function Stepper({steps,active,navigate}:{steps:StepStatus[];active:UploadStep;navigate:(route:Route)=>void}) {
  return <nav className="upload-stepper" aria-label="Upload steps"><ol>{steps.map(item=>
    <li key={item.step} className={`step-${item.state}${item.step===active?' step-active':''}`}>
      <a {...routeLink({page:'upload',step:item.step},navigate)} aria-current={item.step===active?'step':undefined}>
        <span className="step-icon" aria-hidden="true">{item.state==='done'?'✓':item.state==='attention'?'!':item.step}</span>
        <span className="step-text">
          <span className="step-eyebrow">Step {item.step} · {STATE_TEXT[item.state]}</span>
          <strong>{item.label}</strong>
          <small>{item.summary}</small>
        </span>
      </a>
    </li>)}</ol></nav>;
}
