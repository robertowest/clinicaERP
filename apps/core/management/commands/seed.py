"""carga datos de ejemplo: grupo "Grupo Atenea", sus tres clínicas, el catálogo maestro de
especialidades médicas, usuarios/médicos/pacientes de demo (prompt.md §27). idempotente:
puede ejecutarse varias veces sin duplicar registros (reutiliza lo ya existente por
código/nombre/colegiado/nhc).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicos.services import asignar_clinica_especialidad, crear_medico, obtener_medico_de_usuario
from apps.organizacion.services import (
    crear_clinica,
    crear_especialidad,
    crear_grupo,
    obtener_clinica_por_codigo,
    obtener_especialidad_por_nombre,
    obtener_grupo_por_codigo,
)
from apps.pacientes.models import Paciente
from apps.pacientes.services import crear_paciente, obtener_paciente_por_nhc
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles
from apps.usuarios.services import (
    asignar_rol,
    crear_usuario,
    listar_asignaciones,
    obtener_rol_por_codigo,
)

# en desarrollo local `AUTH_PASSWORD_VALIDATORS` está desactivado (development.py), pero
# producción (docker compose) sí los aplica: la contraseña de demo debe superarlos también.
DEMO_PASSWORD = 'DemoClinica2026'

# usuarios de ejemplo por clínica (además del superadmin de plataforma):
# username, rol, código de clínica (None = rol de alcance grupo, sin clínica).
USUARIOS_DEMO = [
    ('atenea.admin', Roles.GROUP_ADMIN, None),
    ('atenea.aldaia.admin', Roles.CLINIC_ADMIN, 'ALDAIA'),
    ('atenea.aldaia.doctor', Roles.DOCTOR, 'ALDAIA'),
    ('atenea.recepcion', Roles.RECEPTIONIST, 'ALDAIA'),
    ('atenea.recepcion', Roles.RECEPTIONIST, 'TORRENT'),
    ('atenea.eliana.doctor', Roles.DOCTOR, 'ELIANA'),
]

# médicos de ejemplo: username (debe estar en USUARIOS_DEMO con rol DOCTOR), colegiado,
# nombre de la especialidad que ejerce en la clínica donde tiene asignado el rol.
MEDICOS_DEMO = [
    ('atenea.aldaia.doctor', 'COL-ALD-001', 'Medicina general'),
    ('atenea.eliana.doctor', 'COL-ELI-001', 'Pediatría'),
]

# pacientes de ejemplo del grupo atenea: nhc, nombre, apellido, documento, fecha de
# nacimiento, sexo.
PACIENTES_DEMO = [
    ('NHC0001', 'Marta', 'García', '11111111A', '1985-03-12', Paciente.Sexo.FEMENINO),
    ('NHC0002', 'Javier', 'Lopez', '22222222B', '1978-07-24', Paciente.Sexo.MASCULINO),
    ('NHC0003', 'Lucía', 'Martínez', '33333333C', '1992-11-02', Paciente.Sexo.FEMENINO),
    ('NHC0004', 'Antonio', 'Sánchez', '44444444D', '1966-01-30', Paciente.Sexo.MASCULINO),
    ('NHC0005', 'Elena', 'Fernández', '55555555E', '2001-09-15', Paciente.Sexo.FEMENINO),
]

# catálogo maestro de especialidades: (nombre, profesión).
ESPECIALIDADES = [
    ('Medicina general', 'Médico de familia'),
    ('Pediatría', 'Pediatra'),
    ('Ginecología y obstetricia', 'Ginecólogo'),
    ('Cardiología', 'Cardiólogo'),
    ('Dermatología', 'Dermatólogo'),
    ('Traumatología', 'Traumatólogo'),
    ('Oftalmología', 'Oftalmólogo'),
    ('Otorrinolaringología', 'Otorrinolaringólogo'),
    ('Psiquiatría', 'Psiquiatra'),
    ('Psicología', 'Psicólogo'),
    ('Fisioterapia', 'Fisioterapeuta'),
    ('Odontología', 'Odontólogo'),
    ('Endocrinología', 'Endocrinólogo'),
    ('Neurología', 'Neurólogo'),
    ('Urología', 'Urólogo'),
    ('Radiología', 'Radiólogo'),
    ('Análisis clínicos', 'Analista clínico'),
    ('Nutrición y dietética', 'Nutricionista'),
]

# clínicas del grupo: (código, nombre, ciudad).
CLINICAS = [
    ('ALDAIA', 'Atenea Aldaia', 'Aldaia'),
    ('TORRENT', 'Atenea Torrent', 'Torrent'),
    ('ELIANA', 'Atenea Eliana', 'La Eliana'),
]


class Command(BaseCommand):
    help = 'Carga datos de ejemplo: Grupo Atenea, sus clínicas y el catálogo de especialidades.'

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_superuser()
        grupo = self._crear_o_reutilizar_grupo()
        especialidades = self._crear_o_reutilizar_especialidades()
        clinicas = self._crear_o_reutilizar_clinicas(grupo, especialidades)
        self._crear_o_reutilizar_usuarios_demo(grupo, clinicas)
        self._crear_o_reutilizar_medicos_demo(clinicas)
        self._crear_o_reutilizar_pacientes_demo(grupo)
        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados correctamente.'))
        self.stdout.write(f"Contraseña de todos los usuarios de demo: {DEMO_PASSWORD}")

    def _seed_superuser(self) -> None:
        if not CustomUser.objects.filter(username='superadmin').exists():
            CustomUser.objects.create_superuser(
                username='superadmin', email='superadmin@example.com', password=DEMO_PASSWORD
            )

    def _crear_o_reutilizar_grupo(self):
        grupo = obtener_grupo_por_codigo('ATENEA')
        if grupo:
            self.stdout.write(f'Grupo ya existente, se reutiliza: {grupo}')
            return grupo
        grupo = crear_grupo(nombre='Grupo Atenea', codigo='ATENEA')
        self.stdout.write(self.style.SUCCESS(f'Grupo creado: {grupo}'))
        return grupo

    def _crear_o_reutilizar_especialidades(self):
        especialidades = []
        for nombre, profesion in ESPECIALIDADES:
            especialidad = obtener_especialidad_por_nombre(nombre)
            if not especialidad:
                especialidad = crear_especialidad(nombre=nombre, profesion=profesion)
                self.stdout.write(f'  Especialidad creada: {especialidad}')
            especialidades.append(especialidad)
        mensaje = f'{len(especialidades)} especialidades disponibles en el catálogo.'
        self.stdout.write(self.style.SUCCESS(mensaje))
        return especialidades

    def _crear_o_reutilizar_clinicas(self, grupo, especialidades):
        clinicas = {}
        for codigo, nombre, ciudad in CLINICAS:
            clinica = obtener_clinica_por_codigo(grupo, codigo)
            if clinica:
                self.stdout.write(f'Clínica ya existente, se reutiliza: {clinica}')
            else:
                clinica = crear_clinica(
                    grupo=grupo, nombre=nombre, codigo=codigo, ciudad=ciudad,
                    especialidades=especialidades,
                )
                self.stdout.write(self.style.SUCCESS(f'Clínica creada: {clinica}'))
            clinicas[codigo] = clinica
        return clinicas

    def _crear_o_reutilizar_usuarios_demo(self, grupo, clinicas):
        for username, rol, codigo_clinica in USUARIOS_DEMO:
            usuario = CustomUser.objects.filter(username=username).first()
            if not usuario:
                usuario = crear_usuario(username=username, password=DEMO_PASSWORD, grupo=grupo)
                self.stdout.write(self.style.SUCCESS(f'Usuario de demo creado: {usuario}'))
            clinica = clinicas[codigo_clinica] if codigo_clinica else None
            rol_obj = obtener_rol_por_codigo(rol)
            asignaciones = listar_asignaciones(usuario=usuario)
            if not asignaciones.filter(clinica=clinica, rol=rol_obj).exists():
                asignar_rol(usuario=usuario, rol=rol_obj, clinica=clinica)
                self.stdout.write(f'  Rol asignado: {usuario} · {rol} ({clinica or "grupo"})')

    def _crear_o_reutilizar_medicos_demo(self, clinicas):
        codigo_clinica_por_username = {
            username: codigo_clinica
            for username, rol, codigo_clinica in USUARIOS_DEMO if rol == Roles.DOCTOR
        }
        for username, colegiado, nombre_especialidad in MEDICOS_DEMO:
            usuario = CustomUser.objects.filter(username=username).first()
            if usuario is None:
                continue
            medico = obtener_medico_de_usuario(usuario)
            if medico is None:
                medico = crear_medico(grupo=usuario.grupo, usuario=usuario, colegiado=colegiado)
                self.stdout.write(self.style.SUCCESS(f'Médico creado: {medico}'))
            clinica = clinicas[codigo_clinica_por_username[username]]
            especialidad = obtener_especialidad_por_nombre(nombre_especialidad)
            if not medico.asignaciones_clinica.filter(clinica=clinica).exists():
                asignar_clinica_especialidad(medico=medico, clinica=clinica, especialidad=especialidad)
                mensaje = f'  Especialidad asignada: {medico} · {especialidad} ({clinica})'
                self.stdout.write(mensaje)

    def _crear_o_reutilizar_pacientes_demo(self, grupo):
        for nhc, nombre, apellido, documento_numero, fecha_nacimiento, sexo in PACIENTES_DEMO:
            if obtener_paciente_por_nhc(grupo, nhc):
                self.stdout.write(f'Paciente ya existente, se reutiliza: {nhc}')
                continue
            paciente = crear_paciente(
                grupo=grupo, nhc=nhc, nombre=nombre, apellido=apellido,
                documento_tipo=Paciente.DocumentoTipo.DNI, documento_numero=documento_numero,
                fecha_nacimiento=fecha_nacimiento, sexo=sexo,
            )
            self.stdout.write(self.style.SUCCESS(f'Paciente creado: {paciente}'))
