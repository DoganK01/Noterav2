from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit,
    QComboBox, QListWidget, QHBoxLayout, QListWidgetItem, QMessageBox, QDateTimeEdit, QFrame
)
from PyQt6.QtCore import QDateTime, Qt, QMimeData, QTimer, QLoggingCategory
from PyQt6.QtGui import QDrag, QColor
import sys

from constants import setStyleSheet, setStyleSheet2, setStyleSheet3

import csv

QLoggingCategory.setFilterRules("qt.qpa.style.*=false")

class KanbanListWidget(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def startDrag(self, actions):
        drag = QDrag(self)
        mime_data = QMimeData()
        selected_items = self.selectedItems()
        if selected_items:
            mime_data.setText(selected_items[0].text())
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def get_priority_color(self, priority: str):
        """Returns a background color based on task priority."""
        if priority == "High":
            return QColor(255, 99, 71)  # Tomato red
        elif priority == "Medium":
            return QColor(255, 165, 0)  # Orange
        elif priority == "Low":
            return QColor(60, 179, 113)  # Medium sea green
        else:
            return QColor(211, 211, 211)  # Light grey (default)

    def dropEvent(self, event):
        if event.mimeData().hasText():
            dropped_task = event.mimeData().text()

            # Check if the task is already in this list
            for i in range(self.count()):
                if self.item(i).text() == dropped_task:
                    return  # Prevent duplicates in the same list

            # Add task to the current list
            self.addItem(dropped_task)
            event.accept()

            # Remove the task from the source list
            source_widget = event.source()
            if source_widget is not self:
                for i in range(source_widget.count()):
                    if source_widget.item(i).text() == dropped_task:
                        source_widget.takeItem(i)
                        break

            task_name = dropped_task.split(" [")[0]
            
            for task in self.window().tasks:
                if task["name"] == task_name:
                    # Set the status to the corresponding list name
                    if self == self.window().todo_list:
                        task["status"] = "To-Do"
                    elif self == self.window().doing_list:
                        task["status"] = "Doing"
                    elif self == self.window().completed_list:
                        task["status"] = "Completed"
                    
                    priority_color = self.get_priority_color(task["priority"])
                    task_item = self.item(self.count() - 1)  # Get the last added item
                    task_item.setBackground(priority_color)  # Set the background color for the task
                    break


class TaskManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Görev Yönetim Uygulaması")
        self.setGeometry(100, 100, 1000, 600)

        self.setStyleSheet(setStyleSheet3)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Top section: Task input
        self.create_task_input_section()

        # Bottom section: Kanban board
        self.create_kanban_board()

        # Task storage
        self.tasks = []

        # Reminder timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(500)  # Check every 500 ms (0.5 seconds)

    def create_task_input_section(self):
        task_input_layout = QVBoxLayout()

        # Task Name
        self.task_label = QLabel("Görev Adı:")
        self.task_input = QLineEdit()
        task_input_layout.addWidget(self.task_label)
        task_input_layout.addWidget(self.task_input)

        # Category
        self.category_label = QLabel("Kategori Etiketi (Opsiyonel):")
        self.category_input = QComboBox()
        self.category_input.addItems(["İş", "Kişisel", "Ev İşleri", "Alışveriş", "Diğer"])
        task_input_layout.addWidget(self.category_label)
        task_input_layout.addWidget(self.category_input)

        # Priority
        self.priority_label = QLabel("Öncelik:")
        self.priority_input = QComboBox()
        self.priority_input.addItems(["Low", "Medium", "High"])  # Replace numeric priorities
        task_input_layout.addWidget(self.priority_label)
        task_input_layout.addWidget(self.priority_input)

        # Reminder
        self.reminder_label = QLabel("Hatırlatıcı (Opsiyonel):")
        self.reminder_input = QDateTimeEdit()
        self.reminder_input.setCalendarPopup(True)
        self.reminder_input.setDateTime(QDateTime.currentDateTime())
        task_input_layout.addWidget(self.reminder_label)
        task_input_layout.addWidget(self.reminder_input)

        # Initial Kanban Status
        self.status_label = QLabel("Başlangıç Durumu:")
        self.status_input = QComboBox()
        self.status_input.addItems(["To-Do", "Doing", "Completed"])
        task_input_layout.addWidget(self.status_label)
        task_input_layout.addWidget(self.status_input)

        # Add Task Button
        self.add_task_button = QPushButton("Görev Ekle")
        self.add_task_button.clicked.connect(self.add_task)
        task_input_layout.addWidget(self.add_task_button)

        # Remove Task Button
        self.remove_task_button = QPushButton("Görev Sil")
        self.remove_task_button.setEnabled(False)  # Initially disabled
        self.remove_task_button.clicked.connect(self.remove_task)
        task_input_layout.addWidget(self.remove_task_button)

        self.unselect_task_button = QPushButton("Seçimi Kaldır")
        self.unselect_task_button.clicked.connect(self.unselect_task)
        task_input_layout.addWidget(self.unselect_task_button)

        self.statistics_button = QPushButton("Görev İstatistiklerini Göster")
        self.statistics_button.clicked.connect(self.show_statistics)
        task_input_layout.addWidget(self.statistics_button)

        self.export_csv_button = QPushButton("Görevleri CSV Olarak Dışa Aktar")
        self.export_csv_button.clicked.connect(self.export_tasks_to_csv)
        task_input_layout.addWidget(self.export_csv_button)

        self.main_layout.addLayout(task_input_layout)

    def create_kanban_board(self):
        kanban_layout = QHBoxLayout()

        # To-Do List
        self.todo_label = QLabel("To-Do")
        self.todo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.todo_list = KanbanListWidget()
        kanban_layout.addWidget(self.create_kanban_column(self.todo_label, self.todo_list))

        # Doing List
        self.doing_label = QLabel("Doing")
        self.doing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.doing_list = KanbanListWidget()
        kanban_layout.addWidget(self.create_kanban_column(self.doing_label, self.doing_list))

        # Completed List
        self.completed_label = QLabel("Completed")
        self.completed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.completed_list = KanbanListWidget()
        kanban_layout.addWidget(self.create_kanban_column(self.completed_label, self.completed_list))

        self.todo_list.itemSelectionChanged.connect(self.on_task_selected)
        self.doing_list.itemSelectionChanged.connect(self.on_task_selected)
        self.completed_list.itemSelectionChanged.connect(self.on_task_selected)

        self.main_layout.addLayout(kanban_layout)

    def create_kanban_column(self, label, list_widget):
        column = QVBoxLayout()
        label.setStyleSheet("background-color: lightblue; color: black; font-weight: bold;")  # Set label color
        list_widget.setStyleSheet("background-color: #f0f8ff;")  # Set list widget color
        column.addWidget(label)
        column.addWidget(list_widget)
        frame = QFrame()
        frame.setLayout(column)
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setStyleSheet("background-color: #e6f7ff; border: 2px solid #007acc;")  # Set frame color
        return frame

    def get_priority_color(self, priority):
        # Determine the color based on priority
        if priority == "Low":
            return Qt.GlobalColor.green
        elif priority == "Medium":
            return Qt.GlobalColor.yellow
        elif priority == "High":
            return Qt.GlobalColor.red
    
    def add_task(self):
        task_name = self.task_input.text()
        category = self.category_input.currentText()
        priority = self.priority_input.currentText()
        reminder_time = self.reminder_input.dateTime().toSecsSinceEpoch()
        current_time = QDateTime.currentDateTime().toSecsSinceEpoch()
        status = self.status_input.currentText()

        if not task_name.strip():
            QMessageBox.warning(self, "Hata", "Görev adı boş olamaz!")
            return

        if reminder_time <= current_time:
            QMessageBox.warning(self, "Hata", "Hatırlatıcı geçmiş bir zamana ayarlanamaz!")
            return

        # Create task
        task = {
            "name": task_name,
            "category": category,
            "priority": priority,
            "reminder": reminder_time if reminder_time > current_time else None,
            "status": status,
            "priority_color": self.get_priority_color(priority)
        }
        self.tasks.append(task)

        # Add to Kanban Board
        task_item = QListWidgetItem(f"{task_name} [Öncelik: {priority}]")
        task_item.setBackground(task["priority_color"])


        if status == "To-Do":
            self.todo_list.addItem(task_item)
        elif status == "Doing":
            self.doing_list.addItem(task_item)
        elif status == "Completed":
            self.completed_list.addItem(task_item)

        self.task_input.clear()
        QMessageBox.information(self, "Başarılı", f"'{task_name}' adlı görev eklendi.")

    def check_reminders(self):
        current_time = QDateTime.currentDateTime().toSecsSinceEpoch()
        for task in self.tasks:
            if task["reminder"] and task["reminder"] <= current_time:
                QMessageBox.information(self, "Hatırlatıcı", f"'{task['name']}' adlı görevi hatırlayın!")
                task["reminder"] = None

    def unselect_task(self):
        # Deselect any selected item
        self.todo_list.clearSelection()
        self.doing_list.clearSelection()
        self.completed_list.clearSelection()
        self.remove_task_button.setEnabled(False)  # Disable the remove button
        QMessageBox.information(self, "Bilgi", "Seçim kaldırıldı.")

    def on_task_selected(self):
        # Check if any task is selected in any list
        current_list = self.sender()  # Identify which list triggered the signal
        if current_list and current_list.currentItem():
            self.remove_task_button.setEnabled(True)  # Enable the remove button when a task is selected
        else:
            self.remove_task_button.setEnabled(False)  # Disable the remove button if no task is selected

    def remove_task(self):
        # Determine which list the task is selected from
        for task_list in [self.todo_list, self.doing_list, self.completed_list]:
            selected_task = task_list.currentRow()
            if selected_task != -1:  # If a task is selected
                task_item = task_list.takeItem(selected_task)
                removed_task_name = task_item.text().split(" [")[0]

                # Remove from the internal task list
                for task in self.tasks:
                    if task["name"] == removed_task_name:
                        self.tasks.remove(task)
                        break

                # Unselect and disable the remove button after task removal
                task_list.clearSelection()
                self.remove_task_button.setEnabled(False)

                QMessageBox.information(self, "Görev Silindi", f"'{removed_task_name}' adlı görev silindi.")
                return

        QMessageBox.warning(self, "Hata", "Lütfen silmek istediğiniz bir görevi seçin!")

    @property
    def total_tasks_count(self):
        return self.todo_list.count() + self.doing_list.count() + self.completed_list.count()

    @property
    def completed_tasks_count(self):
        return self.completed_list.count()
    
    def show_statistics(self):
        total_tasks = self.total_tasks_count
        completed_tasks = self.completed_tasks_count

        if total_tasks == 0:
            QMessageBox.information(self, "İstatistikler", "Henüz hiçbir görev yok.")
            return

        completion_rate = (completed_tasks / total_tasks) * 100
        stats_message = (
            f"Toplam Görev Sayısı: {total_tasks}\n"
            f"Tamamlanan Görev Sayısı: {completed_tasks}\n"
            f"Tamamlama Oranı: {completion_rate:.2f}%"
        )
        QMessageBox.information(self, "Görev İstatistikleri", stats_message)

    def export_tasks_to_csv(self):
        # Define the CSV file name
        file_name = "tasks_export.csv"
        
        # Open the file in write mode
        with open(file_name, mode="w", newline="") as file:
            writer = csv.writer(file)
            
            # Write header
            writer.writerow(["Task Name", "Category", "Priority", "Reminder", "Status"])
            
            # Write task data
            for task in self.tasks:
                reminder = QDateTime.fromSecsSinceEpoch(task["reminder"]).toString() if task["reminder"] else ""
                writer.writerow([task["name"], task["category"], task["priority"], reminder, task["status"]])
        
        QMessageBox.information(self, "Başarılı", f"Tüm görevler '{file_name}' olarak başarıyla kaydedildi.")



# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskManagerApp()
    window.show()
    sys.exit(app.exec())
