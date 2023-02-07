"""Constructor manager main interface."""

from typing import Optional, List
import logging

from qtpy.QtCore import QProcess, QSize, QTimer, Qt, Signal
from qtpy.QtGui import QBrush, QCloseEvent, QMovie
from qtpy.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QProgressBar,
)

from constructor_manager.api import (
    check_updates,
    check_version,
    check_packages,
    restore,
    revert,
    reset,
    open_application,
)
from constructor_manager.utils.worker import ConstructorManagerWorker

# To get mock data
from constructor_manager_ui.data import PackageData

# To setup image resources for .qss file
from constructor_manager_ui.style import images  # noqa

# Packages table constants
RELATED_PACKAGES = 0
ALL_PACKAGES = 1


logger = logging.getLogger(__name__)


class SpinnerWidget(QWidget):
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)

        # Widgets for text and loading gif
        self.text_label = QLabel(text)
        spinner_label = QLabel()
        self.spinner_movie = QMovie(":/images/loading.gif")
        self.spinner_movie.setScaledSize(QSize(18, 18))
        spinner_label.setMovie(self.spinner_movie)

        # Set layout for text + loading indicator
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_label)
        layout.addWidget(spinner_label)
        layout.addStretch(1)
        self.setLayout(layout)
        self.spinner_movie.start()

    def set_text(self, text: str):
        self.text_label.setText(text)

    def show(self):
        try:
            self.spinner_movie.start()
        except RuntimeError:
            pass
        super().show()

    def hide(self):
        try:
            self.spinner_movie.stop()
        except RuntimeError:
            pass
        super().hide()


class UpdateWidget(QWidget):

    install_version = Signal(str)
    skip_version = Signal(str)

    def __init__(self, package_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.package_name = package_name
        self.update_available_version = None

        # Setup widgets
        self.checking_update_widget = SpinnerWidget(
            "Checking for updates...", parent=self
        )
        self.up_to_date_widget = QWidget(self)
        self._initialize_up_to_date_widget()
        self.update_available_widget = QWidget(self)
        self._initialize_update_available_widget()

        # Stack widgets to show one at a time and set layout
        update_widget_layout = QHBoxLayout()
        self.update_widgets = QStackedWidget(self)
        self.update_widgets.addWidget(self.checking_update_widget)
        self.update_widgets.addWidget(self.up_to_date_widget)
        self.update_widgets.addWidget(self.update_available_widget)
        update_widget_layout.addWidget(self.update_widgets)
        self.setLayout(update_widget_layout)

        # Start showing checking updates widget
        self.show_checking_updates_message()

    def _initialize_up_to_date_widget(self):
        up_to_date_layout = QVBoxLayout()
        update_msg_label = QLabel(f"Your {self.package_name} is up to date.")
        up_to_date_layout.addWidget(update_msg_label)

        self.up_to_date_widget.setLayout(up_to_date_layout)

    def _initialize_update_available_widget(self):
        new_version_layout = QVBoxLayout()
        update_msg_label_layout = QHBoxLayout()
        update_msg_label = QLabel(
            f"A newer version of {self.package_name} is available!"
        )
        update_msg_label_layout.addSpacing(15)
        update_msg_label_layout.addWidget(update_msg_label)

        update_actions_layout = QHBoxLayout()
        new_version_label = QLabel(self.update_available_version)
        skip_version_button = QPushButton("Skip This Version")
        install_version_button = QPushButton("Install This Version")
        install_version_button.setObjectName("install_button")
        update_actions_layout.addSpacing(20)
        update_actions_layout.addWidget(new_version_label)
        update_actions_layout.addSpacing(20)
        update_actions_layout.addWidget(skip_version_button)
        update_actions_layout.addSpacing(20)
        update_actions_layout.addWidget(install_version_button)
        update_actions_layout.addStretch(1)
        new_version_layout.addLayout(update_msg_label_layout)
        new_version_layout.addLayout(update_actions_layout)

        self.update_available_widget.setLayout(new_version_layout)

        # Connect buttons signals to parent class signals
        skip_version_button.clicked.connect(
            lambda checked: self.skip_version.emit(self.update_available_version)
        )
        install_version_button.clicked.connect(
            lambda checked: self.install_version.emit(self.update_available_version)
        )

    def show_checking_updates_message(self):
        self.update_widgets.setCurrentWidget(self.checking_update_widget)

    def show_up_to_date_message(self):
        self.update_widgets.setCurrentWidget(self.up_to_date_widget)

    def show_update_available_message(self, update_available_version):
        self.update_available_version = update_available_version
        if update_available_version:
            self.update_widgets.setCurrentWidget(self.update_available_widget)


class PackagesTable(QTableWidget):
    def __init__(self, packages, visible_packages=RELATED_PACKAGES, parent=None):
        super().__init__(parent=parent)
        self.packages = packages
        self.visible_packages = visible_packages
        self.setup()

    def _create_item(self, text: str, related_package: bool):
        item = QTableWidgetItem(text)
        if related_package:
            background_brush = QBrush(Qt.GlobalColor.black)
        else:
            background_brush = QBrush(Qt.GlobalColor.darkGray)

        item.setBackground(background_brush)
        if not related_package:
            foreground_brush = QBrush(Qt.GlobalColor.black)
            item.setForeground(foreground_brush)

        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def setup(self):
        # Set columns number and headers
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Version", "Source", "Build"])
        self.verticalHeader().setVisible(False)

        # Set horizontal headers alignment and config
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Hide table items borders
        self.setShowGrid(False)

        # Set table selection to row
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def set_data(self, packages):
        self.packages = packages

        # Populate table with data available
        for name, version, source, build, related_package in self.packages:
            self.insertRow(self.rowCount())
            package_row = self.rowCount() - 1
            self.setItem(package_row, 0, self._create_item(name, related_package))
            self.setItem(package_row, 1, self._create_item(version, related_package))
            self.setItem(package_row, 2, self._create_item(source, related_package))
            self.setItem(package_row, 3, self._create_item(build, related_package))
            if self.visible_packages == RELATED_PACKAGES and not related_package:
                self.hideRow(package_row)

    def change_visible_packages(self, toggled_option):
        if self.packages:
            self.visible_packages = toggled_option
            if toggled_option == RELATED_PACKAGES:
                for idx, package in enumerate(self.packages):
                    name, version, source, build, related_package = package
                    if not related_package:
                        self.hideRow(idx)
            else:
                for idx, _ in enumerate(self.packages):
                    self.showRow(idx)
        else:
            self.visible_packages = toggled_option

    def change_detailed_info_visibility(self, state):
        if state > Qt.Unchecked:
            self.showColumn(2)
            self.showColumn(3)
            self.change_visible_packages(ALL_PACKAGES)
        else:
            self.hideColumn(2)
            self.hideColumn(3)
            self.change_visible_packages(RELATED_PACKAGES)


class InstallationManagerDialog(QDialog):
    def __init__(
        self,
        package_name: str,
        current_version: Optional[str] = None,
        build_string: Optional[str] = None,
        plugins_url: Optional[str] = None,
        channels: Optional[List[str]] = None,
        dev: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)
        self.package_name = package_name
        self.current_version = current_version
        self.plugins_url = plugins_url
        self.build_string = build_string
        self.channels = channels
        self.dev = dev
        self.snapshot_version = None
        self.updates_widget = None
        self.packages_tablewidget = None
        self.setWindowTitle(f"{package_name} installation manager")
        self.setMinimumSize(QSize(500, 750))
        self.setup_layout()

        self._worker_version = None
        # if current_version is None:
        #     self.current_version_open_button.setVisible(False)
        #     self._worker_version = check_version(self.package_name)
        #     self._worker_version.finished.connect(self._update_version)
        #     self._worker_version.start()
        # else:
        #     self.set_version_actions_enabled(True)

        self._refresh()

    def set_disabled(self, state):
        pass
        # self.packages_tablewidget.setEnabled(not state)
        # self.updates_widget.setEnabled(not state)

    def _refresh(self):
        self._worker_version = check_version(self.package_name)
        self._worker_version.finished.connect(self._update_version)
        self._worker_version.start()

        self._worker_packages = check_packages(
            self.package_name,
            version=self.current_version,
            plugins_url=self.plugins_url,
        )
        self._worker_packages.finished.connect(self._update_packages)
        self._worker_packages.start()

        self._worker_updates = check_updates(
            self.package_name,
            current_version=self.current_version,
            build_string=self.build_string,
            channels=self.channels,
            dev=self.dev,
        )
        self._worker_updates.finished.connect(self._update_widget)
        self._worker_updates.start()

        self.show_checking_updates_message()
        self.set_disabled(True)

    def _update_version(self, result):
        self._handle_finished(result)
        if result.get("exit_code") == 0:
            data = result["data"]
            self.current_version = data.get("version", "")

            if self.current_version:
                text = f"v{self.current_version}"
            else:
                text = "(Not installed!)"

            self.current_version_open_button.setEnabled(bool(self.current_version))

            self.current_version_label.setText(f"{self.package_name} {text}")
            self.set_version_actions_enabled(True)

    def _update_packages(self, result):
        self._handle_finished(result)
        data = result["data"]
        package_data = []
        if isinstance(data, dict):
            packages = data.get("packages", [])
            for pkg in packages:
                package_data.append(
                    PackageData(
                        pkg["name"],
                        pkg["version"],
                        pkg["source"],
                        pkg["build_string"],
                        pkg["is_plugin"],
                    )
                )

        self.set_packages(package_data)

    def _update_widget(self, result):
        self._handle_finished(result)
        if result.get("exit_code") == 0:
            data = result["data"]
            if data.get("update"):
                self.show_update_available_message(data.get("latest_version"))
            else:
                self.show_up_to_date_message()

            self.set_disabled(False)

    def _create_install_information_group(self):
        install_information_group = QGroupBox("Install information")
        install_information_layout = QVBoxLayout()
        current_version_layout = QHBoxLayout()

        # Current version labels and button
        if self.current_version:
            text = f"{self.package_name} v{self.current_version}"
        else:
            text = self.package_name

        self.current_version_label = QLabel(text)
        last_modified_version_label = QLabel()
        # f"Last modified {self.current_version['last_modified']}"
        # )
        self.current_version_open_button = QPushButton("Open")
        self.current_version_open_button.setObjectName("open_button")
        current_version_layout.addWidget(self.current_version_label)
        current_version_layout.addSpacing(10)
        current_version_layout.addWidget(last_modified_version_label)
        current_version_layout.addSpacing(10)
        current_version_layout.addWidget(self.current_version_open_button)
        current_version_layout.addStretch(1)
        install_information_layout.addLayout(current_version_layout)

        # Line to divide current section and update section
        install_version_line = QFrame()
        install_version_line.setObjectName("separator")
        install_version_line.setFrameShape(QFrame.HLine)
        install_version_line.setFrameShadow(QFrame.Sunken)
        install_version_line.setLineWidth(1)
        install_information_layout.addWidget(install_version_line)

        # Update information widget
        self.updates_widget = UpdateWidget(self.package_name, parent=self)
        install_information_layout.addWidget(self.updates_widget)
        install_information_group.setLayout(install_information_layout)

        # Signals
        # Open button signal
        self.current_version_open_button.clicked.connect(self.open_installed)
        # Update widget signals
        self.updates_widget.install_version.connect(self.install_version)
        self.updates_widget.skip_version.connect(self.skip_version)

        return install_information_group

    def _create_packages_group(self):
        packages_group = QGroupBox("Packages")
        packages_layout = QVBoxLayout()

        packages_filter_layout = QHBoxLayout()
        packages_filter_label = QLabel("Show:")
        self.packages_spinner_label = SpinnerWidget("Loading packages...", parent=self)
        show_detailed_view_checkbox = QCheckBox("Detailed view")
        show_detailed_view_checkbox.setChecked(False)

        packages_filter_layout.addWidget(packages_filter_label)
        packages_filter_layout.addWidget(show_detailed_view_checkbox)
        packages_filter_layout.addStretch(1)
        packages_filter_layout.addWidget(self.packages_spinner_label)

        self.packages_tablewidget = PackagesTable(None, parent=self)
        packages_layout.addLayout(packages_filter_layout)
        packages_layout.addWidget(self.packages_tablewidget)
        packages_group.setLayout(packages_layout)

        show_detailed_view_checkbox.stateChanged.connect(
            self.packages_tablewidget.change_detailed_info_visibility
        )
        self.packages_tablewidget.change_detailed_info_visibility(
            show_detailed_view_checkbox.checkState()
        )

        return packages_group

    def _create_installation_actions_group(self):
        installation_actions_group = QGroupBox("Installation Actions")
        installation_actions_layout = QGridLayout()

        # Restore action
        self._restore_button = QPushButton("Restore Installation")
        restore_label = QLabel(
            "Restore installation to the latest snapshot of the current version: "
            # f"{self.snapshot_version['version']} "
            # f"({self.snapshot_version['last_modified']})"
        )
        installation_actions_layout.addWidget(self._restore_button, 0, 0)
        installation_actions_layout.addWidget(restore_label, 0, 1)

        # Revert action
        self._revert_button = QPushButton("Revert Installation")
        revert_label = QLabel(
            "Rollback installation to the latest snapshot of the previous version: "
            # f"{self.snapshot_version['version']} "
            # f"({self.snapshot_version['last_modified']})"
        )
        installation_actions_layout.addWidget(self._revert_button, 1, 0)
        installation_actions_layout.addWidget(revert_label, 1, 1)

        # Reset action
        self._reset_button = QPushButton("Reset Installation")
        reset_label = QLabel(
            "Reset the current installation to clear "
            "preferences, plugins, and other packages"
        )
        installation_actions_layout.addWidget(self._reset_button, 2, 0)
        installation_actions_layout.addWidget(reset_label, 2, 1)

        # Uninstall action
        uninstall_button = QPushButton("Uninstall")
        uninstall_button.setObjectName("uninstall_button")
        uninstall_label = QLabel(
            f"Remove the {self.package_name} Bundled App "
            "and Installation Manager from your computer"
        )
        installation_actions_layout.addWidget(uninstall_button, 3, 0)
        installation_actions_layout.addWidget(uninstall_label, 3, 1)

        # TODO
        self._progress = QProgressBar(self)
        installation_actions_layout.addWidget(self._progress, 4, 0, 1, 2)
        # TODO

        installation_actions_group.setLayout(installation_actions_layout)

        # Signals
        self._restore_button.clicked.connect(self.restore_installation)
        self._revert_button.clicked.connect(self.revert_installation)
        self._reset_button.clicked.connect(self.reset_installation)
        uninstall_button.clicked.connect(self.uninstall)

        return installation_actions_group

    def _create_feedback_group(self):
        feedback_group = QGroupBox("Feedback")
        self._status_data = QTextEdit(self)
        self._status_error = QTextEdit(self)
        # self._progress = QProgressBar(self)

        self._status_data.setReadOnly(True)
        self._status_error.setReadOnly(True)
        self._progress.setTextVisible(False)

        feedback_layout = QVBoxLayout()
        feedback_status_layout = QHBoxLayout()
        feedback_status_layout.addWidget(self._status_data)
        feedback_status_layout.addWidget(self._status_error)

        feedback_layout.addLayout(feedback_status_layout)
        # feedback_layout.addWidget(self._progress)
        feedback_group.setLayout(feedback_layout)
        # feedback_group.setVisible(False)
        return feedback_group

    def setup_layout(self):
        main_layout = QVBoxLayout(self)

        # Install information
        install_information_group = self._create_install_information_group()
        main_layout.addWidget(install_information_group, stretch=2)

        # Packages
        packages_group = self._create_packages_group()
        main_layout.addWidget(packages_group, stretch=2)

        # Installation Actions
        installation_actions_group = self._create_installation_actions_group()
        main_layout.addWidget(installation_actions_group, stretch=2)

        # Installation Actions
        feedback_group = self._create_feedback_group()
        main_layout.addWidget(feedback_group, stretch=1)

        # Layout
        self.setLayout(main_layout)

        self.set_version_actions_enabled(False)

    def open_installed(self):
        self._open_worker = open_application(self.package_name, self.current_version)
        self._open_worker.start()
        self.current_version_open_button.setEnabled(False)

        # Disable open button for a bit
        self._timer_open_button = QTimer()
        self._timer_open_button.timeout.connect(
            lambda: self.current_version_open_button.setEnabled(True)
        )
        self._timer_open_button.setSingleShot(True)
        self._timer_open_button.start(10000)

    def show_checking_updates_message(self):
        self.updates_widget.show_checking_updates_message()

    def show_up_to_date_message(self):
        self.updates_widget.show_up_to_date_message()

    def show_update_available_message(self, update_available_version):
        self.updates_widget.show_update_available_message(update_available_version)

    def install_version(self, update_version):
        # TODO: To be handled with the backend.
        #       Maybe this needs to be a signal
        print(update_version)

    def skip_version(self, skip_version):
        # TODO: To be handled with the backend.
        #       Maybe this needs to be a signal
        print(skip_version)

    def set_packages(self, packages):
        self.packages_spinner_label.show()
        self.packages = packages
        if self.packages_tablewidget:
            self.packages_tablewidget.set_data(self.packages)
            self.packages_spinner_label.hide()

    def _handle_finished(self, result):
        self._status_data.append("<br>")
        self._status_error.append("<br>")
        data = result.get("data", {})
        error = result.get("error", "")
        self._status_data.append(str(data))
        self._status_error.append(str(error))

    def handle_finished(self, result):
        self._handle_finished(result)
        self.set_busy(False)
        self._refresh()

    def restore_installation(self):
        print("Restore installation")
        worker = restore(self.package_name)
        worker.finished.connect(self.handle_finished)
        worker.start()
        self.set_busy(True)

    def revert_installation(self):
        print("Revert installation")
        worker = revert(self.package_name)
        worker.finished.connect(self.handle_finished)
        worker.start()
        self.set_busy(True)

    def reset_installation(self):
        print("Reset installation")
        self._worker = reset(
            package_name=self.package_name,
            current_version=self.current_version,
            channels=self.channels,
        )
        self._worker.finished.connect(self.handle_finished)
        self._worker.start()
        self.set_busy(True)

    def uninstall(self):
        # TODO: To be handled with the backend.
        #       Maybe this needs to be a signal
        print("Uninstall")
        self.set_busy(False)

    def set_busy(self, value):
        if value:
            # self._status.setText("")
            self._progress.setValue(0)
            self._progress.setMinimum(0)
            self._progress.setMaximum(0)
        else:
            self._progress.setValue(0)
            self._progress.setMinimum(0)
            self._progress.setMaximum(1)
            self._progress.reset()

        self._restore_button.setDisabled(value)
        self._revert_button.setDisabled(value)
        self._reset_button.setDisabled(value)

    def set_version_actions_enabled(self, value):
        self._restore_button.setEnabled(value)
        self._revert_button.setEnabled(value)
        self._reset_button.setEnabled(value)
        self.current_version_open_button.setVisible(value)

    def _terminate_worker(self, worker):
        not_running = QProcess.ProcessState.NotRunning
        if worker and worker.state() != not_running:
            self._worker_version.terminate()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Override Qt method."""
        while ConstructorManagerWorker._WORKERS:
            worker = ConstructorManagerWorker._WORKERS.pop()
            self._terminate_worker(worker)

        return super().closeEvent(event)

