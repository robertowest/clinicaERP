"""carga datos de ejemplo: grupo "Grupo Atenea", sus tres clínicas y el catálogo
maestro de especialidades médicas. idempotente: puede ejecutarse varias veces sin
duplicar registros (reutiliza lo ya existente por código/nombre).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizacion.services import (
    crear_clinica,
    crear_especialidad,
    crear_grupo,
    obtener_clinica_por_codigo,
    obtener_especialidad_por_nombre,
    obtener_grupo_por_codigo,
)
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles
from apps.usuarios.services import (
    asignar_rol,
    crear_usuario,
    listar_asignaciones,
    obtener_rol_por_codigo,
)

DEMO_PASSWORD = 'demo'

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
