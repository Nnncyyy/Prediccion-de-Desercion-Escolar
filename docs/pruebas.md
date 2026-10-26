# PT — Plan de pruebas inicial

- PT_01 Inicio de sesión: credenciales válidas → JWT; inválidas → HTTP 401.
- PT_02 Alumnos: alta válida → HTTP 201; matrícula repetida → HTTP 409.
- PT_03 Calificaciones: registrar nota 0..10; fuera de rango → HTTP 422.
- PT_04 IA: ejecutar entrenamiento; validar tamaño, etiquetas y métricas del test sin ajuste en test.
- PT_05 Alertas: sin calificaciones → sin_datos; 2 reprobadas y trabajo 30 h → alta; no etiquetar como probabilidad ML.
- PT_06 Dashboard: conteos según BD.
- PT_07 Seguridad: endpoint privado sin token → 401/403.
- PT_08 Integración: crear estudiante + materia + inscripción y consultar alerta.
- PT_09 Manual: ejecutar desde clon limpio con .env configurado.

Cada ejecución debe incluir ID, fecha, versión, responsable, entrada, salida esperada, resultado observado, estado, evidencia y defecto si aplica.
