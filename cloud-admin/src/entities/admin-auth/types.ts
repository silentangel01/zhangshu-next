export interface AdminLoginRequest {
  email: string
  password: string
}

export interface AdminMeResponse {
  id: string
  email: string
  display_name: string
}
