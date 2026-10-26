import { ApiClient, defaultApi } from './api/client';
import { useRoute } from './routing';
import { useWorkspace, type PageProps } from './store/useWorkspace';
import { AppShell } from './shell/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { CasesPage } from './pages/CasesPage';
import { CasePage } from './pages/CasePage';
import { AssistantPage } from './pages/AssistantPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { useApprovalQueue } from './approvals/useApprovalQueue';

export default function App({api=defaultApi}:{api?:ApiClient}) {
  const ws=useWorkspace(api);
  const [route,navigate]=useRoute();
  const props:PageProps={ws,route,navigate};
  // The Approvals badge reads the same shared store as the Approvals page; no number while it loads.
  const approvals=useApprovalQueue(ws).items?.length??null;
  return <AppShell {...props} approvals={approvals}>{
    route.page==='upload'?<UploadPage {...props}/>:
    route.page==='cases'?<CasesPage {...props}/>:
    // A case page belongs to one workspace and case; switching either starts a fresh page.
    route.page==='case'?<CasePage key={`${ws.selected??''}:${route.caseId}`} {...props}/>:
    route.page==='assistant'?<AssistantPage {...props}/>:
    route.page==='approvals'?<ApprovalsPage {...props}/>:
    <DashboardPage {...props}/>
  }</AppShell>;
}
