import { Box, TextField, Button, Stack, Typography } from '@mui/material'
import { useForm } from 'react-hook-form'

type SettingsForm = {
  timezone: string
  cancellation_hours: number
  payment_provider: string
}

const SettingsPage = () => {
  const { register, handleSubmit } = useForm<SettingsForm>({
    defaultValues: {
      timezone: 'Europe/Moscow',
      cancellation_hours: 24,
      payment_provider: 'yookassa'
    }
  })

  const onSubmit = (data: SettingsForm) => {
    console.log('Settings saved', data)
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <Stack spacing={2} maxWidth={400}>
        <Typography variant="h6">Настройки студии</Typography>
        <TextField label="Таймзона" {...register('timezone')} />
        <TextField label="Часы до отмены" type="number" {...register('cancellation_hours', { valueAsNumber: true })} />
        <TextField label="Провайдер оплаты" {...register('payment_provider')} />
        <Button type="submit" variant="contained">Сохранить</Button>
      </Stack>
    </Box>
  )
}

export default SettingsPage
