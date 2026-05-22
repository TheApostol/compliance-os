'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TicketingRoot() {
  const router = useRouter()
  useEffect(() => { router.replace('/ticketing/dashboard') }, [router])
  return null
}
