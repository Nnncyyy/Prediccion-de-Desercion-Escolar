export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export type Student = {id:number;enrollment_number:string;full_name:string;program:string;semester:number;employed:boolean;work_hours_weekly:number};
export type Subject = {id:number;code:string;name:string;credits:number};
export type Enrollment = {id:number;student_id:number;subject_id:number;term:string;grade:number|null};
export type Alert = {student_id:number;level:string;average:number|null;failed_subjects:number;evaluated_subjects:number;reasons:string[];method:string};
export async function request<T>(endpoint:string,token:string,options:RequestInit={}):Promise<T>{
 const response=await fetch(`${API}/api${endpoint}`,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}});
 if(!response.ok){let err='Error de solicitud';try{let j=await response.json();err=typeof j.detail==='string'?j.detail:JSON.stringify(j.detail||j)}catch{}throw new Error(err)}
 return response.json();
}
